import stripe
from decimal import Decimal
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from .models import Wallet, Transaction
from accounts.models import User

stripe.api_key = settings.STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET = settings.STRIPE_WEBHOOK_SECRET


class StripeWebhookAddFundsView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        except (ValueError, stripe.error.SignatureVerificationError):
            return Response({"error": "Invalid payload or signature"}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ SUCCESS
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            email = session.get("customer_email")
            payment_id = session.get("payment_intent")
            amount = session["metadata"].get("amount")
            payment_method = session["metadata"].get("payment_method", "Stripe")

            try:
                user = User.objects.get(email=email)
                wallet, _ = Wallet.objects.get_or_create(user=user)

                # Convert to Decimal
                wallet.reel_bux_balance += Decimal(amount)
                wallet.save(update_fields=["reel_bux_balance", "updated_at"])

                Transaction.objects.create(
                    user=user,
                    source="stripe",
                    tx_type="fund",
                    amount=Decimal(amount),
                    balance_type="reelbux",
                    status="success",
                    reference_id=payment_id,
                    description=f"Wallet top-up via {payment_method}"
                )

                print(f"✅ Added {amount} to {email}'s wallet")
            except User.DoesNotExist:
                print(f"No user found with email {email}")

        # FAILED PAYMENT
        elif event["type"] == "payment_intent.payment_failed":
            intent = event["data"]["object"]
            email = intent.get("metadata", {}).get("email")
            amount = intent.get("metadata", {}).get("amount", "0")
            payment_id = intent.get("id")
            payment_method = intent.get("metadata", {}).get("payment_method", "Stripe")

            try:
                user = User.objects.get(email=email)
                Transaction.objects.create(
                    user=user,
                    source="stripe",
                    tx_type="fund",
                    amount=Decimal(amount),
                    balance_type="reelbux",
                    status="failed",
                    reference_id=payment_id,
                    description=f"Failed wallet top-up via {payment_method}"
                )
                print(f"Failed payment recorded for {email}")
            except User.DoesNotExist:
                print(f"No user found with email {email}")

        return Response({"status": "success"}, status=status.HTTP_200_OK)
