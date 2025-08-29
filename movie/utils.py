from datetime import timedelta, date
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate, TruncWeek
from .models import Film, FilmView
from subscription.models import Transaction

# daily view counts for the last 7 days
def get_daily_views(film_id):
    """
    Return daily view counts for the last 7 days (including today)
    for the given film_id.
    """
    try:
        film = Film.objects.get(id=film_id)
    except Film.DoesNotExist:
        return None  # Film not found

    today = date.today()
    last_7_days = today - timedelta(days=6)

    views = (
        FilmView.objects.filter(film=film, viewed_at__date__gte=last_7_days)
        .annotate(day=TruncDate("viewed_at"))
        .values("day")
        .annotate(total_views=Count("id"))
        .order_by("day")
    )

    result = []
    for i in range(7):
        day = last_7_days + timedelta(days=i)
        day_views = next((v["total_views"] for v in views if v["day"] == day), 0)
        result.append({
            "day": str(day),
            "total_views": day_views
        })

    # keep it in variable for flexibility
    data = {
        "film": film.title,
        "film_id": film.id,
        "daily_views": result
    }
    return data



# total earnings per week for the last 7 weeks
def get_weekly_earnings(film_id):
    """
    Return total earnings per week for the last 7 weeks for a given film_id.
    Only considers successful 'purchase' and 'rent' transactions.
    """
    today = date.today()
    last_7_weeks_start = today - timedelta(weeks=6)  # last 7 weeks including this week

    # Filter only film purchase/rent and successful transactions
    earnings_qs = (
        Transaction.objects.filter(
            film_id=film_id,
            tx_type__in=["purchase", "rent"],
            status="success",
            created_at__date__gte=last_7_weeks_start
        )
        .annotate(week=TruncWeek("created_at"))
        .values("week")
        .annotate(total_earning=Sum("amount"))
        .order_by("week")
    )

    # Convert to dict for faster lookup
    earnings_dict = {e["week"].date(): float(e["total_earning"] or 0) for e in earnings_qs}

    result = []
    for i in range(7):
        week_start = last_7_weeks_start + timedelta(weeks=i)
        result.append({
            "week_start": str(week_start),
            "total_earning": earnings_dict.get(week_start, 0.0)
        })
    
    # keep it in variable for flexibility
    data = {
        "film_id": film_id,
        "weekly_earnings": result
    }
    return data