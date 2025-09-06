import uuid
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view

import paypalrestsdk

from .models import Film, MyFilms
from accounts.models import User
from subscription.models import Wallet, Transaction


# ---------------- PAYPAL CONFIG ----------------
paypalrestsdk.configure({
    "mode": "sandbox",  # "live" for production
    "client_id": settings.PAYPAL_CLIENT_ID,
    "client_secret": settings.PAYPAL_CLIENT_SECRET,
})


# ---------------- CREATE FILM RENTED ----------------
class CreatePaypalFilmRentedView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        film_id = request.data.get("film_id")
        referral_code = request.data.get("distro_code")
        price = request.data.get("rent_price")
        rent_hour = request.data.get("rent_hour")

        film = Film.objects.filter(id=film_id).first()
        if not film:
            return Response({"message": "Film not found"}, status=404)

        if not price:
            return Response({"message": "Need rent_price"}, status=400)

        try:
            price = Decimal(price).quantize(Decimal("0.01"))
        except Exception:
            return Response({"message": "Invalid rent_price format"}, status=400)

        if price <= 0:
            return Response({"message": "Invalid rent_price"}, status=400)

        if not rent_hour:
            return Response({"message": "Need rent_hour"}, status=400)

        # Check if user already owns the film
        if MyFilms.objects.filter(user=user, film=film, status="active").exists():
            return Response({"message": "You already own this film"}, status=400)

        txn_id = f"rent_{uuid.uuid4().hex[:12]}"

        # Create PayPal payment
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "redirect_urls": {
                "return_url": request.build_absolute_uri(
                    reverse("movie:paypal_rented_execute")
                ) + f"?film_id={film.id}&txn_id={txn_id}&ref={referral_code or ''}&rent_hour={rent_hour}",
                "cancel_url": request.build_absolute_uri(
                    reverse("movie:paypal_rented_cancel")
                ),
            },
            "transactions": [{
                "item_list": {"items": [{
                    "name": f"Rented Film: {film.title}",
                    "sku": str(uuid.uuid4()),
                    "price": f"{price:.2f}",
                    "currency": "USD",
                    "quantity": 1,
                }]},
                "amount": {"total": f"{price:.2f}", "currency": "USD"},
                "description": f"Rented {film.title}",
            }],
        })

        if payment.create():
            approval_url = next(link.href for link in payment.links if link.rel == "approval_url")
            token = approval_url.split("token=")[1]

            # Log pending transaction
            Transaction.objects.create(
                user=user,
                film=film,
                source="paypal",
                tx_type="rent",
                amount=price.quantize(Decimal("0.01")),
                status="pending",
                txn_id=txn_id,
                paypal_token=token,
                description=f"Pending PayPal rent for {film.title}"
            )
            return Response({"approvalUrl": approval_url})

        return Response({"message": payment.error}, status=500)


# ---------------- EXECUTE FILM RENTED ----------------
class ExecutePaypalFilmRentedView(APIView):
    authentication_classes = []  # PayPal redirect (no JWT required)
    permission_classes = []

    def get(self, request):
        payment_id = request.query_params.get("paymentId")
        payer_id = request.query_params.get("PayerID")
        film_id = request.query_params.get("film_id")
        txn_id = request.query_params.get("txn_id")
        referral_code = request.query_params.get("ref")
        rent_hour = request.query_params.get("rent_hour")

        film = Film.objects.filter(id=film_id).first()
        if not film:
            return Response({"message": "Film not found"}, status=404)

        platform_user = User.objects.filter(is_platform=True).first()
        if not platform_user:
            return Response({"message": "Platform user not configured"}, status=500)

        try:
            payment = paypalrestsdk.Payment.find(payment_id)
        except Exception as e:
            return Response({"message": f"Payment not found: {str(e)}"}, status=400)

        if not payer_id:
            Transaction.objects.filter(txn_id=txn_id, status="pending").update(status="failed")
            return Response({"status": "cancelled", "message": "User cancelled at PayPal."})

        if payment.execute({"payer_id": payer_id}):
            try:
                with transaction.atomic():
                    transaction_obj = Transaction.objects.select_related("user").get(
                        txn_id=txn_id, status="pending"
                    )
                    transaction_obj.status = "completed"
                    transaction_obj.txn_id = payment_id
                    transaction_obj.save()

                    user = transaction_obj.user
                    price = transaction_obj.amount

                    # 🔑 Extract PayPal fee details
                    try:
                        sale = payment.transactions[0].related_resources[0].sale
                        sale_obj = paypalrestsdk.Sale.find(sale.id)

                        gross_amount = Decimal(sale_obj.amount["total"])
                        paypal_fee = Decimal(sale_obj.transaction_fee["value"])
                        net_amount = (gross_amount - paypal_fee).quantize(Decimal("0.01"))
                    except Exception:
                        gross_amount = transaction_obj.amount
                        paypal_fee = Decimal("0.00")
                        net_amount = gross_amount

                    # ---- Record Film ownership ----
                    MyFilms.objects.create(
                        user=user,
                        film=film,
                        access_type="Rent",
                        txn_id=txn_id,
                        price=gross_amount,
                        start_date=timezone.now(),
                        end_date=timezone.now() + timedelta(hours=int(rent_hour or 0)),
                        status="active",
                    )

                    # ---- Revenue Split (net based) ----
                    filmmaker_share = (net_amount * Decimal("0.70")).quantize(Decimal("0.01"))
                    affiliate_share = Decimal("0.00")
                    platform_share = (net_amount - filmmaker_share).quantize(Decimal("0.01"))

                    # ---- Affiliate commission ----
                    if referral_code:
                        referrer = User.objects.filter(distro_code=referral_code).first()
                        if referrer and referrer != user:
                            affiliate_share = (net_amount * Decimal("0.20")).quantize(Decimal("0.01"))
                            filmmaker_share = (net_amount * Decimal("0.70")).quantize(Decimal("0.01"))
                            platform_share = (net_amount - filmmaker_share - affiliate_share).quantize(Decimal("0.01"))

                            # Credit affiliate wallet
                            aff_wallet, _ = Wallet.objects.get_or_create(user=referrer)
                            aff_wallet.distro_balance += affiliate_share
                            aff_wallet.save()

                            Transaction.objects.create(
                                user=referrer,
                                film=film,
                                source="paypal",
                                tx_type="commission",
                                amount=affiliate_share,
                                txn_id=f"aff_{txn_id}",
                                balance_type="distro",
                                status="completed",
                                description=f"Affiliate commission for film {film.title}",
                            )

                    # ---- Filmmaker payout ----
                    if film.filmmaker:
                        maker_wallet, _ = Wallet.objects.get_or_create(user=film.filmmaker)
                        maker_wallet.reel_bux_balance += filmmaker_share
                        maker_wallet.save()

                        Transaction.objects.create(
                            user=film.filmmaker,
                            film=film,
                            source="paypal",
                            tx_type="filmmaker_earning",
                            amount=filmmaker_share,
                            txn_id=f"maker_{txn_id}",
                            balance_type="reelbux",
                            status="completed",
                            description=f"Earning for film {film.title}",
                        )

                    # ---- Platform payout ----
                    platform_wallet, _ = Wallet.objects.get_or_create(user=platform_user)
                    platform_wallet.reel_bux_balance += platform_share
                    platform_wallet.save()

                    Transaction.objects.create(
                        user=platform_user,
                        film=film,
                        source="paypal",
                        tx_type="platform_earning",
                        amount=platform_share,
                        txn_id=f"platform_{txn_id}",
                        balance_type="reelbux",
                        status="completed",
                        description=f"Platform earning for film {film.title}",
                    )

                    # ---- Update buyer transaction with net amount and fee ----
                    transaction_obj.amount = price
                    transaction_obj.status = "completed"
                    transaction_obj.description = f"Paid {price} USD for {film.title} (PayPal fee: {paypal_fee})"
                    transaction_obj.save(update_fields=["amount", "status", "description"])

            except Exception as e:
                return Response({"message": "Failed to record rented", "error": str(e)}, status=500)

            return Response({
                "status": "success",
                "film": film.title,
                "gross": str(gross_amount),
                "paypal_fee": str(paypal_fee),
                "net": str(net_amount),
                "filmmaker_share": str(filmmaker_share),
                "affiliate_share": str(affiliate_share),
                "platform_share": str(platform_share),
            })

        # Payment failed
        Transaction.objects.filter(txn_id=txn_id).update(status="failed")
        return Response({"message": payment.error}, status=400)


# ---------------- CANCEL FILM RENTED ----------------
@api_view(["GET"])
def paypal_film_rented_cancel_view(request):
    token = request.GET.get("token")
    if token:
        Transaction.objects.filter(paypal_token=token, status="pending").update(status="failed")
    return Response({"status": "cancelled", "message": "Film rented cancelled"})
