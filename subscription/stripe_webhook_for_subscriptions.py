
import stripe
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from .models import UserSubscription, SubscriptionPlan
from accounts.models import User

stripe.api_key = settings.STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET = settings.STRIPE_WEBHOOK_SECRET


class StripeWebhookSubscriptionView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            return Response({"message": "Invalid payload"}, status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError:
            return Response({"message": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)

        # Handle checkout session completed
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            subscription_id = session.get("subscription")
            email = session.get("customer_email")  # use Stripe customer email
            plan_name = session["metadata"].get("plan")
            duration_days = int(session["metadata"].get("duration_days", 30))
            limit_value = int(session["metadata"].get("limit_value", 0))

            handle_subscription_started(email, plan_name, duration_days, limit_value, subscription_id)

        # Handle subscription renewal payment success
        elif event["type"] == "invoice.payment_succeeded":
            invoice = event["data"]["object"]
            subscription_id = invoice.get("subscription")
            email = invoice.get("customer_email")
            handle_subscription_renewal(email, subscription_id)

        # Handle payment failures
        elif event["type"] == "invoice.payment_failed":
            invoice = event["data"]["object"]
            subscription_id = invoice.get("subscription")
            email = invoice.get("customer_email")
            handle_subscription_payment_failed(email, subscription_id)

        return Response({"status": "success"}, status=status.HTTP_200_OK)


def handle_subscription_started(email, plan_name, duration_days, limit_value, subscription_id):
    try:
        user = User.objects.get(email=email)
        user.is_subscribe = True
        user.save()

        # Get plan price from SubscriptionPlan
        plan_obj = SubscriptionPlan.objects.filter(name=plan_name).first()
        plan_price = plan_obj.price if plan_obj else 0

        # Calculate period end
        period_end = timezone.now() + timedelta(days=duration_days)

        # Create or update subscription
        subscription, created = UserSubscription.objects.update_or_create(
            subscription_id=subscription_id,
            defaults={
                "user": user,
                "plan_name": plan_name,
                "price": plan_price,
                "current_period_start": timezone.now(),
                "current_period_end": period_end,
                "limit_value": limit_value,
                "payment_method": "stripe",
                "status": "active",
                "payment_status": "completed",
                "cancel_at_period_end": False,
            },
        )

        print(f"Subscription activated for user {email}.")
    except User.DoesNotExist:
        print(f"No user found with email {email}.")


def handle_subscription_renewal(email, subscription_id):
    try:
        subscription = UserSubscription.objects.filter(subscription_id=subscription_id).first()
        if subscription:
            # Extend period by same duration as original plan
            plan_obj = SubscriptionPlan.objects.filter(name=subscription.plan_name).first()
            duration_days = plan_obj.duration_days if plan_obj else 30
            subscription.current_period_start = timezone.now()
            subscription.current_period_end = timezone.now() + timedelta(days=duration_days)
            subscription.status = "active"
            subscription.payment_status = "completed"
            subscription.save()
            print(f"Subscription renewed for user {email}.")
        else:
            print(f"No subscription found with ID {subscription_id} to renew.")
    except Exception as e:
        print(f"Error renewing subscription for {email}: {e}")


def handle_subscription_payment_failed(email, subscription_id):
    try:
        subscription = UserSubscription.objects.filter(subscription_id=subscription_id).first()
        if subscription:
            subscription.payment_status = "failed"
            subscription.status = "past_due"
            subscription.save()
            print(f"Payment failed for user {email}, subscription marked as past_due.")
        else:
            print(f"No subscription found with ID {subscription_id} for failed payment.")
    except Exception as e:
        print(f"Error handling failed payment for {email}: {e}")
