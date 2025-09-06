import stripe
from decimal import Decimal, ROUND_DOWN
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.http import JsonResponse
from django.urls import reverse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from accounts.models import User
from subscription.models import Wallet, Transaction
from .models import Film, MyFilms

stripe.api_key = settings.STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET = settings.STRIPE_WEBHOOK_SECRET

# -------------------- Checkout Session --------------------
class CreateStripePurchaseCheckoutSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        film_id = request.data.get("film_id")
        referral_code = request.data.get("distro_code", "")
        payment_method = "stripe"

        film = Film.objects.filter(id=film_id).first()
        if not film:
            return Response({"message": "Film not found"}, status=404)

        price = film.buy_price
        if price <= 0:
            return Response({"message": "Invalid film price"}, status=400)

        # Already owns
        if MyFilms.objects.filter(user=user, film=film, status="active").exists():
            return Response({"message": "You already own this film"}, status=400)

        try:
            checkout_session = stripe.checkout.Session.create(
                mode="payment",
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": film.title},
                        "unit_amount": int(Decimal(price) * 100),
                    },
                    "quantity": 1,
                }],
                customer_email=user.email,
                metadata={
                    "user_id": str(user.id),
                    "film_id": str(film.id),
                    "referral_code": referral_code,
                    "amount": str(price),
                    "payment_method": payment_method,
                },
                success_url=request.build_absolute_uri(
                    reverse("movie:stripe_purchase_checkout_success")
                ) + "?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=request.build_absolute_uri(
                    reverse("movie:stripe_purchase_checkout_cancel")
                ),
            )
        except Exception as e:
            return Response({"message": str(e)}, status=500)

        return Response({
            "sessionId": checkout_session.id,
            "checkoutUrl": checkout_session.url,
        })


# -------------------- Success / Cancel --------------------
def stripe_purchase_checkout_success_view(request):
    return JsonResponse({
        "status": "success",
        "message": "Film purchased successfully."
    })


def stripe_purchase_checkout_cancel_view(request):
    return JsonResponse({
        "status": "cancelled",
        "message": "Film purchase cancelled."
    })



#@M.Alom
# -------------------- Stripe Webhook --------------------
class StripeWebhookPurchaseView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        except ValueError:
            return Response({"message": "Invalid payload"}, status=400)
        except stripe.error.SignatureVerificationError:
            return Response({"message": "Invalid signature"}, status=400)

        # ---------------- SUCCESS ----------------
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            payment_id = session.get("payment_intent")
            user_id = session["metadata"].get("user_id")
            film_id = session["metadata"].get("film_id")
            referral_code = session["metadata"].get("referral_code", "")
            amount = Decimal(session["metadata"].get("amount", "0"))
            payment_method = session["metadata"].get("payment_method", "stripe")

            try:
                user = User.objects.get(id=user_id)
                film = Film.objects.get(id=film_id)
                platform_user = User.objects.filter(is_platform=True).first()
                if not platform_user:
                    return Response({"message": "Platform user not configured"}, status=500)

                # Stripe payment info
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
                    

                # ---------- Save Purchase + Revenue Split ----------
                with transaction.atomic():
                    # Buyer Transaction
                    Transaction.objects.create(
                        user=user,
                        film=film,
                        source="stripe",
                        tx_type="purchase",
                        amount=amount,
                        status="completed",
                        txn_id=payment_id,
                        description=f"Paid {amount} USD for {film.title} (Stripe fee: {stripe_fee})"
                    )

                    # Film ownership
                    MyFilms.objects.get_or_create(
                        user=user,
                        film=film,
                        defaults={
                            "access_type": "Buy",
                            "txn_id": payment_id,
                            "price": amount,
                            "start_date": timezone.now(),
                            "status": "active"
                        }
                    )

                    # Revenue Split
                    filmmaker_share = (net_amount * Decimal("0.70")).quantize(Decimal("0.01"))
                    affiliate_share = Decimal("0.00")
                    platform_share = (net_amount - filmmaker_share).quantize(Decimal("0.01"))

                    # Affiliate
                    if referral_code:
                        referrer = User.objects.filter(distro_code=referral_code).first()
                        if referrer and referrer != user:
                            affiliate_share = (net_amount * Decimal("0.20")).quantize(Decimal("0.01"))
                            platform_share = (net_amount - filmmaker_share - affiliate_share).quantize(Decimal("0.01"))

                            aff_wallet, _ = Wallet.objects.get_or_create(user=referrer)
                            aff_wallet.distro_balance += affiliate_share
                            aff_wallet.save()

                            Transaction.objects.create(
                                user=referrer,
                                film=film,
                                source="stripe",
                                tx_type="commission",
                                amount=affiliate_share,
                                balance_type="distro",
                                txn_id=f"aff_{payment_id}",
                                status="completed",
                                description=f"Affiliate commission for {film.title}"
                            )

                    # Filmmaker payout
                    if film.filmmaker:
                        maker_wallet, _ = Wallet.objects.get_or_create(user=film.filmmaker)
                        maker_wallet.reel_bux_balance += filmmaker_share
                        maker_wallet.save()

                        Transaction.objects.create(
                            user=film.filmmaker,
                            film=film,
                            source="stripe",
                            tx_type="filmmaker_earning",
                            amount=filmmaker_share,
                            balance_type="reelbux",
                            txn_id=f"maker_{payment_id}",
                            status="completed",
                            description=f"Filmmaker earning for {film.title}"
                        )

                    # Platform payout
                    platform_wallet, _ = Wallet.objects.get_or_create(user=platform_user)
                    platform_wallet.reel_bux_balance += platform_share
                    platform_wallet.save()

                    Transaction.objects.create(
                        user=platform_user,
                        film=film,
                        source="stripe",
                        tx_type="platform_earning",
                        amount=platform_share,
                        balance_type="reelbux",
                        txn_id=f"platform_{payment_id}",
                        status="completed",
                        description=f"Platform earning for {film.title}"
                    )

                    # ---- Update Film total earning & total buy earning ----
                    film.total_earning = (film.total_earning or Decimal("0.00")) + filmmaker_share.quantize(Decimal("0.00"))
                    film.total_buy_earning = (film.total_buy_earning or Decimal("0.00")) + filmmaker_share.quantize(Decimal("0.00"))
                    film.save(update_fields=["total_earning", "total_buy_earning"])

                return Response({"status": "success"}, status=200)

            except Exception as e:
                return Response({"message": str(e)}, status=500)

        # ---------------- FAILED PAYMENT ----------------
        elif event["type"] == "payment_intent.payment_failed":
            intent = event["data"]["object"]
            email = intent.get("metadata", {}).get("email")
            amount = Decimal(intent.get("metadata", {}).get("amount", "0"))
            payment_id = intent.get("id")
            try:
                user = User.objects.get(email=email)
                Transaction.objects.create(
                    user=user,
                    source="stripe",
                    tx_type="purchase",
                    amount=amount,
                    status="failed",
                    txn_id=payment_id,
                    description="Failed film purchase"
                )
            except User.DoesNotExist:
                pass

        return Response({"status": "ignored"}, status=200)
