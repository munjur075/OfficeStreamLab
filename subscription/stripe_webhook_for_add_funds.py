import stripe
import logging
from decimal import Decimal, ROUND_DOWN
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from .models import Wallet, Transaction
from accounts.models import User

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET = settings.STRIPE_WEBHOOK_SECRET


class StripeWebhookAddFundsView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
        except ValueError as e:
            logger.error(f"⚠️ Invalid payload: {e}")
            return Response({"message": "Invalid payload"}, status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"⚠️ Invalid signature: {e}")
            return Response({"message": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)

        # ------------------ SUCCESS ------------------
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            payment_id = session.get("payment_intent")
            print(payment_id)

            user_id = session["metadata"].get("user_id")
            email = session.get("customer_email")
            amount = session["metadata"].get("amount", "0")
            payment_method = session["metadata"].get("payment_method", "Stripe")

            try:
                user = None
                if user_id:
                    user = User.objects.filter(id=user_id).first()
                if not user and email:
                    user = User.objects.filter(email=email).first()

                if not user:
                    logger.error(f"❌ No user found for email={email}, user_id={user_id}")
                    return Response({"message": "User not found"}, status=404)

                wallet, _ = Wallet.objects.get_or_create(user=user)

                if payment_id:
                    payment_intent = stripe.PaymentIntent.retrieve(payment_id)
                    charge = stripe.Charge.retrieve(payment_intent.latest_charge)
                    # print(charge)

                    if charge.balance_transaction:
                        balance_tx = stripe.BalanceTransaction.retrieve(charge.balance_transaction)
                        gross_amount = (Decimal(balance_tx.amount) / 100).quantize(Decimal("0.01"))
                        stripe_fee   = (Decimal(balance_tx.fee) / 100).quantize(Decimal("0.01"))
                        net_amount   = (Decimal(balance_tx.net) / 100).quantize(Decimal("0.01"))
                    else:
                        # fallback if balance_transaction not yet available
                        gross_amount = Decimal(session.get("amount_total") or session["metadata"].get("amount", "0")) / 100

                        # estimate Stripe fee: 2.9% + $0.30
                        stripe_fee = (gross_amount * Decimal("0.029") + Decimal("0.30")).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
                        # net amount to credit wallet
                        net_amount = (gross_amount - stripe_fee).quantize(Decimal("0.01"), rounding=ROUND_DOWN)

                        logger.warning(f"⚠️ balance_transaction missing for payment {payment_id}, "
                                    f"using session amount. Estimated Stripe fee: {stripe_fee}, Net: {net_amount}")

                # ✅ Credit wallet only with net amount
                wallet.reel_bux_balance += net_amount
                wallet.save(update_fields=["reel_bux_balance", "updated_at"])

                Transaction.objects.create(
                    user=user,
                    source="stripe",
                    tx_type="fund",
                    amount=net_amount,
                    balance_type="reelbux",
                    status="completed",
                    txn_id=payment_id,
                    description=f"Wallet top-up via {payment_method} "
                                f"(Gross: {gross_amount}, Fee: {stripe_fee}, Net: {net_amount})"
                )

                logger.info(f"✅ Added {net_amount} to {user.email}'s wallet (gross {gross_amount}, fee {stripe_fee})")

            except Exception as e:
                logger.exception(f"Error handling successful payment: {e}")

        # ------------------ FAILED PAYMENT ------------------
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
                    txn_id=payment_id,
                    description=f"Failed wallet top-up via {payment_method}"
                )
                print(f"Failed payment recorded for {email}")
            except User.DoesNotExist:
                print(f"No user found with email {email}")

        return Response({"status": "success"}, status=status.HTTP_200_OK)
