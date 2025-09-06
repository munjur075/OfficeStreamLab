import uuid
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .models import Film, MyFilms
from accounts.models import User
from subscription.models import Wallet, Transaction



class FilmRentedReelBuxView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        film_id = request.data.get("film_id")
        referral_code = request.data.get("distro_code")  # optional

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

        # 1. Get platform/system user (dedicated platform user recommended)
        platform_user = User.objects.filter(is_platform=True, is_superuser=True).first()
        if not platform_user:
            return Response({"message": "Platform user not configured"}, status=500)

        # Generate unique transaction ID
        txn_id = f"buy_{uuid.uuid4().hex[:12]}"

        try:
            with transaction.atomic():
                # --- Wallet creation inside atomic transaction ---
                wallet, _ = Wallet.objects.select_for_update().get_or_create(user=user)

                if wallet.reel_bux_balance < price:
                    return Response({"message": "Insufficient ReelBux balance"}, status=status.HTTP_400_BAD_REQUEST)

                # Deduct buyer's balance
                wallet.reel_bux_balance -= price
                wallet.save()
                
                # ---- Buyer transaction log ----
                Transaction.objects.create(
                    user=user,
                    film=film,
                    source="reelbux",
                    tx_type="rent",
                    amount=price,
                    txn_id=txn_id,
                    balance_type="reelbux",
                    status="completed",
                    description=f"Debit {price} ReelBux for film rented",
                )

                # 2. Create MyFilms entry
                MyFilms.objects.create(
                    user=user,
                    film=film,
                    access_type="Rent",
                    txn_id=txn_id,
                    price=price,
                    start_date=timezone.now(),
                    end_date=timezone.now() + timedelta(hours=int(rent_hour or 0)),
                    status="active"
                )

                # 3. Revenue split
                filmmaker_share = price * Decimal("0.70")
                affiliate_share = Decimal("0.00")
                platform_share = price * Decimal("0.30")

                # ---- Affiliate commission ----
                if referral_code:
                    referrer = User.objects.filter(distro_code=referral_code).first()
                    if referrer and referrer != user:
                        affiliate_share = price * Decimal("0.20")
                        filmmaker_share = price * Decimal("0.70")
                        platform_share = price - (filmmaker_share + affiliate_share)

                        # credit affiliate wallet
                        aff_wallet, _ = Wallet.objects.get_or_create(user=referrer)
                        aff_wallet.distro_balance += affiliate_share
                        aff_wallet.save()

                        # log affiliate transaction
                        Transaction.objects.create(
                            user=referrer,
                            film=film,
                            source="reelbux",
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
                        source="reelbux",
                        tx_type="filmmaker_earning",
                        amount=filmmaker_share,
                        txn_id=f"maker_{txn_id}",
                        balance_type="reelbux",
                        status="completed",
                        description=f"Earning for film {film.title}",
                    )

                # ---- Platform/systems payout ----
                platform_wallet, _ = Wallet.objects.get_or_create(user=platform_user)
                platform_wallet.reel_bux_balance += platform_share
                platform_wallet.save()

                Transaction.objects.create(
                    user=platform_user,
                    film=film,
                    source="reelbux",
                    tx_type="platform_earning",
                    amount=platform_share,
                    txn_id=f"platform_{txn_id}",
                    balance_type="reelbux",
                    status="completed",
                    description=f"Platform earning for film {film.title}",
                )
                # ---- Update Film total earning & total rent earning ----
                film.total_earning = (film.total_earning or Decimal("0.00")) + filmmaker_share.quantize(Decimal("0.00"))
                film.total_rent_earning = (film.total_rent_earning or Decimal("0.00")) + filmmaker_share.quantize(Decimal("0.00"))
                film.save(update_fields=["total_earning", "total_rent_earning"])

        except Exception as e:
            return Response({"message": "Rented failed", "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            "message": "Film rented successfully",
            "film": film.title,
            "subscription_id": txn_id,
            "new_balance": wallet.reel_bux_balance,
            "filmmaker_share": filmmaker_share,
            "affiliate_share": affiliate_share,
            "platform_share": platform_share,
        }, status=status.HTTP_201_CREATED)
