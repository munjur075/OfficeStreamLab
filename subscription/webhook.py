#
import stripe, json
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from .models import UserSubscription
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime

User = get_user_model()
stripe.api_key = settings.STRIPE_SECRET_KEY

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    ev_type = event["type"]
    obj = event["data"]["object"]

    # 1) Checkout completed -> subscription created
    if ev_type == "checkout.session.completed":
        # session contains 'subscription' and metadata if set
        session = obj
        subscription_id = session.get("subscription")
        metadata = session.get("metadata", {}) or session.get("subscription_data", {}).get("metadata", {})
        # prefer metadata sent earlier
        user_id = metadata.get("django_user_id")
        plan = metadata.get("plan") or session.get("display_items", [{}])[0].get("plan", {}).get("nickname")

        # fetch full subscription details
        sub = stripe.Subscription.retrieve(subscription_id)
        price_id = sub["items"]["data"][0]["price"]["id"]
        current_period_end = datetime.fromtimestamp(sub["current_period_end"], tz=timezone.utc)

        return HttpResponse(user_id)

        if user_id:
            try:
                user = User.objects.get(id=int(user_id))
                user.subscription = plan
                user.save()
                Subscription.objects.update_or_create(
                    stripe_subscription_id=subscription_id,
                    defaults={
                        "user": user,
                        "stripe_price_id": price_id,
                        "plan": plan or "",
                        "status": sub["status"],
                        "current_period_end": current_period_end,
                        "cancel_at_period_end": sub.get("cancel_at_period_end", False),
                    }
                )
            except User.DoesNotExist:
                # handle orphan subscription or log
                pass

    # 2) Subscription updated/deleted or invoice events -> update DB
    elif ev_type in ("customer.subscription.updated", "customer.subscription.deleted"):
        sub = obj
        subscription_id = sub["id"]
        try:
            s = Subscription.objects.get(stripe_subscription_id=subscription_id)
            s.status = sub.get("status", s.status)
            s.cancel_at_period_end = sub.get("cancel_at_period_end", s.cancel_at_period_end)
            try:
                s.current_period_end = datetime.fromtimestamp(sub["current_period_end"], tz=timezone.utc)
            except Exception:
                pass
            s.save()
        except Subscription.DoesNotExist:
            # optionally create or log
            pass

    elif ev_type == "invoice.payment_succeeded":
        # update invoice / subscription status if needed
        invoice = obj
        subscription_id = invoice.get("subscription")
        # mark subscription active, etc.
        if subscription_id:
            Subscription.objects.filter(stripe_subscription_id=subscription_id).update(status="active")

    elif ev_type == "invoice.payment_failed":
        invoice = obj
        subscription_id = invoice.get("subscription")
        if subscription_id:
            Subscription.objects.filter(stripe_subscription_id=subscription_id).update(status="past_due")

    # Acknowledge receipt
    return HttpResponse(status=200)