import random
from decimal import Decimal
from django.db.models import Sum, Count, Min
from django.db.models.functions import TruncDate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from subscription.models import Wallet, Transaction
from movie.models import Film


class MyDistroView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Top 10 trending films
        top_trending = list(Film.objects.filter(status="PUBLISHED").order_by('-unique_views')[:10])

        # Pick 3 random films from top 10
        random_films = random.sample(top_trending, min(3, len(top_trending)))

        # Convert to JSON-serializable format
        random_films_data = [
            {
                "film_id": film.id,
                "film_title": film.title,
                "film_type": film.get_film_type_display(),
                "quick_copy": f"https://equal-evidently-terrier.ngrok-free.app/distro/{film.id}"
            }
            for film in random_films
        ]

        # User distro code URL
        distro_code = getattr(user, "distro_code", None)
        if distro_code:
            distro_url = f"https://equal-evidently-terrier.ngrok-free.app/distro/{distro_code}"
        else:
            distro_url = None

        # Get or create wallet for this user
        wallet, _ = Wallet.objects.get_or_create(user=user)

        # Filter only commission transactions for this user
        my_distro = Transaction.objects.filter(user=user, tx_type="commission")

        # ---- overall stats ----
        stats = my_distro.aggregate(
            commission_sum=Sum("amount"),
            total_clicks=Count("id")
        )

        commission_sum = stats["commission_sum"] or Decimal("0.00")
        total_clicks = stats["total_clicks"] or 0

        # ---- per film stats ----
        per_film = (
            my_distro
            .values("film__id", "film__title")   # group by film
            .annotate(
                film_clicks=Count("id"),
                film_earning=Sum("amount"),
                first_click_date=TruncDate(Min("created_at")),  # date only
            )
            .order_by("-film_earning")
        )

        per_film_stats = [
            {
                "film_id": row["film__id"],
                "film_title": row["film__title"],
                "first_click_date": row["first_click_date"],
                "film_clicks": row["film_clicks"],
                "film_earning": (row["film_earning"] or Decimal("0.00")).quantize(Decimal("0.00")),
                "status": "Completed"
            }
            for row in per_film
        ]

        return Response({
            "status": "success",
            "message": "Wallet fetched successfully",
            "total_earning": commission_sum.quantize(Decimal("0.00")),
            "total_clicks": total_clicks,
            "distro_balance": Decimal(wallet.distro_balance).quantize(Decimal("0.00")),
            "distro_urls": distro_url,
            "random_popular_films": random_films_data,
            "per_film": per_film_stats
        })
