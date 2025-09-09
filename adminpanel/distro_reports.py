from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from subscription.models import Transaction
from django.db.models import Sum, Count
from decimal import Decimal
from django.utils import timezone

class FilmDistroReportView(APIView):
    """
    Distributor report including overall stats, user-wise earnings & clicks,
    and top 3 monthly earning users.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        # Current month range
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Filter only commission transactions
        distro_earning = Transaction.objects.filter(tx_type="commission")

        # ---- overall stats ----
        stats = distro_earning.aggregate(
            total_earning=Sum("amount"),
            total_clicks=Count("id")
        )

        total_earning = stats["total_earning"] or Decimal("0.00")
        total_clicks = stats["total_clicks"] or 0

        # ---- user-wise stats (all time) ----
        user_wise_stats = (
            distro_earning
            .values("user__id", "user__full_name")
            .annotate(
                user_total_earning=Sum("amount"),
                user_total_clicks=Count("id")
            )
            .order_by("-user_total_earning")
        )

        user_wise = [
            {
                "user_id": u["user__id"],
                "full_name": u["user__full_name"],
                "total_earning": Decimal(u["user_total_earning"] or 0).quantize(Decimal("0.00")),
                "total_clicks": u["user_total_clicks"],
                "status": "Completed"
            }
            for u in user_wise_stats
        ]

        # ---- top 3 monthly stats ----
        monthly_stats = (
            distro_earning
            .filter(created_at__gte=month_start)   # Assuming Transaction has created_at
            .values("user__id", "user__full_name")
            .annotate(
                monthly_earning=Sum("amount"),
                monthly_clicks=Count("id")
            )
            .order_by("-monthly_earning")[:3]
        )

        top3_monthly = [
            {
                "user_id": u["user__id"],
                "full_name": u["user__full_name"],
                "monthly_earning": Decimal(u["monthly_earning"] or 0).quantize(Decimal("0.00")),
                "monthly_clicks": u["monthly_clicks"]
            }
            for u in monthly_stats
        ]

        return Response({
            "status": "success",
            "message": "Distro fetched successfully",
            "total_earning": Decimal(total_earning).quantize(Decimal("0.00")),
            "total_clicks": total_clicks,
            "user_wise": user_wise,
            "top_3_monthly_users": top3_monthly
        })
