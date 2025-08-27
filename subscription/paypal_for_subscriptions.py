import uuid
from datetime import timedelta
from django.conf import settings
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from accounts.models import User

from .models import UserSubscription, SubscriptionPlan
import paypalrestsdk

# -------------------- PAYPAL CONFIG --------------------
paypalrestsdk.configure({
    "mode": "sandbox",  # change to "live" in production
    "client_id": settings.PAYPAL_CLIENT_ID,
    "client_secret": settings.PAYPAL_CLIENT_SECRET,
})


# -------------------- CREATE PAYMENT --------------------
class CreatePaypalCheckoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user

        if UserSubscription.objects.filter(user=user, status="active").exists():
            return Response({"message": "You already have an active subscription."}, status=200)

        data = request.data
        plan_name = data.get("plan", "Basic")
        duration_days = int(data.get("duration_days", 30))
        limit_value = int(data.get("limit_value", 0))
        currency = data.get("currency", "USD")

        plan = SubscriptionPlan.objects.filter(name=plan_name).first()
        if not plan:
            return Response({"error": "Invalid plan"}, status=400)

        subscription_price = plan.price
        total_str = f"{subscription_price:.2f}"

        # Create PayPal Payment
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "redirect_urls": {
                "return_url": request.build_absolute_uri(reverse("subscription:paypal_execute")),
                "cancel_url": request.build_absolute_uri(reverse("subscription:paypal_cancel")),
            },
            "transactions": [{
                "item_list": {"items": [{
                    "name": plan_name,
                    "sku": str(uuid.uuid4()),
                    "price": total_str,
                    "currency": currency,
                    "quantity": 1,
                }]},
                "amount": {"total": total_str, "currency": currency},
                "description": f"{plan_name} subscription",
            }],
        })

        if payment.create():
            # Extract EC-XXX token from approval_url
            approval_url = next(link.href for link in payment.links if link.rel == "approval_url")
            token = approval_url.split("token=")[1]

            # Save subscription with both IDs
            UserSubscription.objects.create(
                user=user,
                plan_name=plan_name,
                payment_method="paypal",
                subscription_id=payment.id,  # PAY-XXX
                paypal_token=token,          # EC-XXX
                price=subscription_price,
                limit_value=limit_value,
                current_period_start=timezone.now(),
                current_period_end=timezone.now() + timedelta(days=duration_days),
                cancel_at_period_end=False,
                payment_status="pending",
                status="pending",
            )
            return Response({"approvalUrl": approval_url})

        return Response({"error": payment.error}, status=500)


# -------------------- EXECUTE PAYMENT --------------------
class ExecutePaypalPaymentView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        payment_id = request.query_params.get("paymentId")
        payer_id = request.query_params.get("PayerID")

        if not payment_id:
            return Response({"error": "Missing paymentId"}, status=400)

        try:
            payment = paypalrestsdk.Payment.find(payment_id)
        except Exception as e:
            return Response({"error": f"Payment not found: {str(e)}"}, status=400)

        # If user cancelled (missing PayerID)
        if not payer_id:
            UserSubscription.objects.filter(
                subscription_id=payment_id, payment_status="pending"
            ).update(payment_status="Failed", status="canceled")
            return Response({"status": "cancelled", "message": "User cancelled at PayPal."}, status=200)

        # If payment execution success
        if payment.execute({"payer_id": payer_id}):
            try:
                subscription = UserSubscription.objects.select_related("user").get(subscription_id=payment_id)
                subscription.payment_status = "completed"
                subscription.status = "active"
                subscription.save()

                # Mark user as subscribed
                subscription.user.is_subscribe = True
                subscription.user.save()

                return JsonResponse({"status": "success", "message": "Subscription activated successfully!"})

            except UserSubscription.DoesNotExist:
                return Response({"error": "Subscription record not found."}, status=404)

        # If execution failed
        UserSubscription.objects.filter(subscription_id=payment_id).update(
            payment_status="Failed", status="canceled"
        )
        return Response({"error": payment.error}, status=400)


# -------------------- CANCEL PAYMENT --------------------
def paypal_cancel_view(request):
    token = request.GET.get("token")

    if token:
        UserSubscription.objects.filter(paypal_token=token, payment_status="pending").update(
            payment_status="Failed", status="canceled"
        )

    return JsonResponse({"status": "cancelled", "message": "Subscription was cancelled by user."})
