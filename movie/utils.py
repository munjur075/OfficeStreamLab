# from datetime import timedelta, date
# from django.db.models import Count, Sum
# from django.db.models.functions import TruncDate, TruncWeek
# from .models import Film, FilmView
# from subscription.models import Transaction

# # daily view counts for the last 7 days
# def get_daily_views(film_id):
#     """
#     Return daily view counts for the last 7 days (including today)
#     for the given film_id, with progress proportional to views.
#     """

#     today = date.today()
#     last_7_days = [today - timedelta(days=i) for i in reversed(range(7))]  # oldest → newest

#     # Get views in last 7 days
#     views_qs = (
#         FilmView.objects.filter(film=film_id, viewed_at__date__gte=last_7_days[0])
#         .annotate(day=TruncDate("viewed_at"))
#         .values("day")
#         .annotate(total_views=Count("id"))
#     )

#     # Make dict for easy lookup
#     views_dict = {v["day"]: v["total_views"] for v in views_qs}

#     # Total views over 7 days
#     total_views = sum(views_dict.get(day, 0) for day in last_7_days) or 1  # avoid div by zero

#     result = []
#     for day in last_7_days:
#         day_views = views_dict.get(day, 0)
#         progress = (day_views / total_views) * 100 if total_views else 0
#         result.append({
#             "day": str(day),
#             "total_views": day_views,
#             "progress_value": round(progress, 2)  # round to 2 decimal places
#         })


#     return result



# # total earnings per week for the last 7 weeks
# def get_weekly_earnings(film_id):
#     """
#     Return total earnings per week for the last 7 weeks for a given film_id.
#     Includes progress proportional to earnings.
#     Only considers successful 'purchase' and 'rent' transactions.
#     """
#     today = date.today()
#     last_7_weeks_start = today - timedelta(weeks=6)  # last 7 weeks including this week

#     # Query earnings
#     earnings_qs = (
#         Transaction.objects.filter(
#             film_id=film_id,
#             tx_type__in=["purchase", "rent"],
#             status="success",
#             created_at__date__gte=last_7_weeks_start
#         )
#         .annotate(week=TruncWeek("created_at"))
#         .values("week")
#         .annotate(total_earning=Sum("amount"))
#         .order_by("week")
#     )

#     # Dict for easy lookup
#     earnings_dict = {e["week"].date(): float(e["total_earning"] or 0) for e in earnings_qs}

#     # Total earnings across 7 weeks
#     week_starts = [last_7_weeks_start + timedelta(weeks=i) for i in range(7)]
#     total_earnings = sum(earnings_dict.get(week, 0) for week in week_starts) or 1  # avoid div by zero

#     # Build result with progress
#     result = []
#     for week_start in week_starts:
#         earning = earnings_dict.get(week_start, 0)
#         progress = (earning / total_earnings) * 100 if total_earnings else 0
#         result.append({
#             "week_start": str(week_start),
#             "total_earning": earning,
#             "progress_value": round(progress, 2)
#         })

#     return result

# # Daily Views (Last 7 Days) Average watch time
# def get_last_7_days_analytics(film_id):
#     """
#     Returns last 7 days daily views with progress and average watch time.
#     Progress is based on Film.total_views (every play).
#     Average watch time uses watched_seconds from FilmView.
#     """

#     try:
#         film = Film.objects.get(id=film_id)
#     except Film.DoesNotExist:
#         return None

#     today = date.today()
#     last_7_days = [today - timedelta(days=i) for i in reversed(range(7))]  # oldest → newest

#     # Aggregate daily watched seconds
#     views_qs = FilmView.objects.filter(
#         film=film, viewed_at__date__gte=last_7_days[0]
#     ).annotate(day=TruncDate('viewed_at')).values('day').annotate(
#         daily_watched_seconds=Sum('watched_seconds'),
#         daily_unique_views=Count('id')
#     )

#     # Dict for easy lookup
#     watched_dict = {v['day']: v['daily_watched_seconds'] for v in views_qs}
#     unique_views_dict = {v['day']: v['daily_unique_views'] for v in views_qs}

#     # Build daily result with progress based on Film.total_views
#     result = []
#     total_views_last7days = sum(unique_views_dict.values()) or 1  # unique views for last 7 days

#     for day in last_7_days:
#         watched_sec = watched_dict.get(day, 0)
#         day_unique_views = unique_views_dict.get(day, 0)
#         progress = (day_unique_views / total_views_last7days) * 100 if total_views_last7days else 0
#         result.append({
#             "day": str(day),
#             "unique_views": day_unique_views,
#             "watched_seconds": watched_sec,
#             "progress_value": round(progress, 2)
#         })

#     # Average watch time (per play)
#     total_watched_seconds = sum(watched_dict.values())
#     average_watch_time_seconds = total_watched_seconds / (film.total_views or 1)

#     data = {
#         "daily_views": result,
#         "average_watch": round(average_watch_time_seconds, 2)
#     }

#     return data


# from datetime import date, timedelta
# from django.db.models import Count
# from django.utils.timezone import now
# from .models import FilmView, FilmPlayView

# def get_last_7_days_views(film):
#     today = date.today()
#     last_7_days = [today - timedelta(days=i) for i in range(6, -1, -1)]

#     daily_stats = []

#     for day in last_7_days:
#         # Total plays (all sessions)
#         total_views = FilmPlayView.objects.filter(
#             film=film, viewed_at__date=day
#         ).count()

#         # Unique viewers (distinct users per day)
#         unique_views = FilmPlayView.objects.filter(
#             film=film, viewed_at__date=day
#         ).values("viewer").distinct().count()

#         daily_stats.append({
#             "date": day.strftime("%Y-%m-%d"),
#             "total_views": total_views,
#             "unique_views": unique_views,
#         })

#     return daily_stats

