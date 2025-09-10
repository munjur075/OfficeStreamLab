from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.db.models import Sum, Count, Q
from decimal import Decimal
from subscription.models import Transaction
from movie.views import MyPagination


class FilmTransactionOverview(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        # ------------------- Transactions (only purchase & rent) -------------------
        transactions = Transaction.objects.filter(
            tx_type__in=["purchase", "rent"]
        ).select_related("user")

        # ------------------- Earnings (1 query) -------------------
        earnings = transactions.aggregate(
            completed=Sum("amount", filter=Q(status="completed")),
            pending=Sum("amount", filter=Q(status="pending")),
            failed=Sum("amount", filter=Q(status="failed")),
        )

        stats = {
            "total_completed_earning": float(earnings["completed"] or Decimal(0)),
            "total_pending_earning": float(earnings["pending"] or Decimal(0)),
            "total_failed_earning": float(earnings["failed"] or Decimal(0)),
        }

        # ------------------- Transfer status counts (1 query) -------------------
        counts = transactions.aggregate(
            completed=Count("id", filter=Q(status="completed")),
            pending=Count("id", filter=Q(status="pending")),
            failed=Count("id", filter=Q(status="failed")),
        )

        transfer_status = {
            "completed_count": counts["completed"],
            "pending_count": counts["pending"],
            "failed_count": counts["failed"],
        }

        # ------------------- Payment methods (transaction count per method) -------------------
        method_totals = transactions.values("source").annotate(total=Count("id"))
        total_count = sum(m["total"] or 0 for m in method_totals)

        # Prepare all payment methods (even if 0 transactions)
        all_methods = ["stripe", "paypal", "reelbux"]
        method_dict = {m["source"]: m["total"] for m in method_totals}

        payment_overview = {}
        for method in all_methods:
            count = int(method_dict.get(method, 0) or 0)
            payment_overview[method.capitalize()] = {
                "total": count,
                "percentage": round(count / total_count * 100, 2) if total_count else 0,
            }

        # ------------------- Transaction list -------------------
        transaction_list = [
            {
                "tx_type": t.tx_type,
                "user": t.user.full_name,
                "amount": float(t.amount),
                "payment_method": t.source,
                "date": t.created_at.date(),
                "status": t.get_status_display(),
            }
            for t in transactions
        ]

        # ------------------- Pagination only for transactions -------------------
        paginator = MyPagination()
        paginated_transactions = paginator.paginate_queryset(transaction_list, request)

        pagination_data = {
            "count": paginator.page.paginator.count,
            "total_pages": paginator.page.paginator.num_pages,
            "current_page": paginator.page.number,
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link(),
        }

        # ------------------- Final Response -------------------
        return Response({
            "status": "success",
            "message": "Payments Overview fetched successfully",
            "stats": stats,
            "transfer_status": transfer_status,
            "payment_method": payment_overview,
            "transactions_list": paginated_transactions,
            "pagination": pagination_data,
        })
