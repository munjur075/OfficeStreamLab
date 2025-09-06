from rest_framework.views import APIView
import cloudinary
import cloudinary.uploader
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404, render
from rest_framework.permissions import IsAuthenticated
from .models import Film, Genre, FilmView, FilmPlayView
from .serializers import FilmSerializer, FilmListSerializer, GenreSerializer
from datetime import date, timedelta
from django.db.models import Sum
from subscription.models import Transaction


class FilmUploadView(APIView):
    """
    Upload a film with thumbnail, trailer, and full film.
    Generates multi-resolution HLS URLs via Cloudinary.
    """
    def post(self, request, *args, **kwargs):
        try:
            title = request.data.get("title")
            year = request.data.get("year")
            logline = request.data.get("logline")
            film_type = request.data.get("film_type")
            genre_names = request.data.get("genre")
            rent_price = request.data.get("rent_price", 0)
            buy_price = request.data.get("buy_price", 0)

            thumbnail_file = request.FILES.get("thumbnail")
            trailer_file = request.FILES.get("trailer")
            full_film_file = request.FILES.get("full_film")

            # 1️⃣ Upload thumbnail
            thumbnail_result = cloudinary.uploader.upload(
                thumbnail_file,
                folder="thumbnails/"
            )
            thumbnail_url = thumbnail_result.get("secure_url")

            # 2️⃣ Upload trailer (multi-bitrate HLS)
            trailer_result = cloudinary.uploader.upload_large(
                file=trailer_file,
                resource_type="video",
                folder="trailers/",
                eager=[{'format': 'hls'}],  # Multi-bitrate HLS
                eager_async=True
            )
            trailer_public_id = trailer_result.get("public_id")
            trailer_hls_url = f"https://res.cloudinary.com/{cloudinary.config().cloud_name}/video/upload/{trailer_public_id}.m3u8"

            # 3️⃣ Upload full film (multi-bitrate HLS)
            full_film_result = cloudinary.uploader.upload_large(
                file=full_film_file,
                resource_type="video",
                folder="full_films/",
                eager=[{'format': 'hls'}],  # Multi-bitrate HLS
                eager_async=True
            )
            full_film_public_id = full_film_result.get("public_id")
            film_hls_url = f"https://res.cloudinary.com/{cloudinary.config().cloud_name}/video/upload/{full_film_public_id}.m3u8"
            full_film_duration = full_film_result.get("duration")

            # 4️⃣ Create Film instance
            film = Film.objects.create(
                title=title,
                year=year,
                logline=logline,
                film_type=film_type,
                rent_price=rent_price,
                buy_price=buy_price,
                filmmaker=request.user,
                thumbnail=thumbnail_url,
                trailer_public_id=trailer_public_id,
                full_film_public_id=full_film_public_id,
                trailer_hls_url=trailer_hls_url,
                film_hls_url=film_hls_url,
                full_film_duration=full_film_duration
            )

            # 5️⃣ Set genres
            if genre_names:
                genre_list = genre_names.split(",")
                genres = Genre.objects.filter(name__in=genre_list)
                film.genre.set(genres)

            film.save()
            serializer = FilmSerializer(film)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
def cloudinary_webhook(request):
    """
    Updates HLS URLs and duration after Cloudinary finishes processing large videos.
    Ensures multi-resolution streaming works in production.
    """
    if request.method != "POST":
        return JsonResponse({"message": "Invalid method"}, status=400)

    try:
        payload = json.loads(request.body)
        print(payload)
        public_id = payload.get("public_id")
        resource_type = payload.get("resource_type")
        duration = payload.get("duration")
        eager_process = payload.get("eager")
        print("egar process start:",eager_process)

        film = None
        if Film.objects.filter(trailer_public_id=public_id).exists():
            film = Film.objects.get(trailer_public_id=public_id)
        elif Film.objects.filter(full_film_public_id=public_id).exists():
            film = Film.objects.get(full_film_public_id=public_id)

        if not film:
            return JsonResponse({"message": "Film not found"}, status=404)

        if resource_type == "video":
            if duration:
                film.full_film_duration = duration

            # Master HLS URL for adaptive streaming
            film.film_hls_url = f"https://res.cloudinary.com/{cloudinary.config().cloud_name}/video/upload/{public_id}.m3u8"

        film.save()
        return JsonResponse({"status": "success", "film_id": film.id})

    except Exception as e:
        return JsonResponse({"message": str(e)}, status=400)

    
class FilmDetailsView(APIView):
    """
    Returns details of a specific published film by its ID, 
    including related movies.
    """
    def get(self, request):
        film_id = request.data.get("film_id")
        # film_id = request.GET.get("film_id", "").strip()

        # Fetch film with case-insensitive status check
        film = get_object_or_404(Film, id=film_id, status__iexact='published')

        # Build film details
        film_details = {
            "id": film.id,
            # "filmmaker": str(film.filmmaker),
            "title": film.title,
            "slug":film.slug,
            "year": film.year,
            "logline": film.logline,
            "film_type": film.get_film_type_display(),
            "genre": [g.name for g in film.genre.all()] if hasattr(film.genre, "all") else film.genre,
            # "status": film.status,
            "buy_price": film.buy_price,
            "rent_price": film.rent_price,
            # "rental_hours": film.rental_hours,
            "full_film_duration": film.full_film_duration,
            # "unique_views": film.unique_views,
            # "total_earning": film.total_earning,
            "thumbnail": film.thumbnail.url if film.thumbnail else None,
            "trailer_hls_url": film.trailer_hls_url,
        }

        # 🔹 Fetch related films by shared genre
        if hasattr(film.genre, "all"):
            related_films = Film.objects.filter(
                genre__in=film.genre.all(),
                status__iexact='published'
            ).exclude(id=film.id).distinct()[:10]
        else:
            related_films = Film.objects.filter(
                genre=film.genre,
                status__iexact='published'
            ).exclude(id=film.id)[:10]

        related_data = [
            {
                "id": f.id,
                # "filmmaker": str(f.filmmaker),
                "title": f.title,
                "slug":f.slug,
                "year": f.year,
                "logline": f.logline,
                "film_type": f.get_film_type_display(),
                "genre": [g.name for g in f.genre.all()] if hasattr(f.genre, "all") else f.genre,
                # "status": f.status,
                "buy_price": f.buy_price,
                "rent_price": f.rent_price,
                # "rental_hours": f.rental_hours,
                "full_film_duration": f.full_film_duration,
                # "unique_views": f.unique_views,
                # "total_earning": f.total_earning,
                "thumbnail": f.thumbnail.url if f.thumbnail else None,
                "trailer_hls_url": f.trailer_hls_url,
            }
            for f in related_films
        ]

        return Response({
            "status": "success",
            "message": "Film details fetched successfully",
            "film_details": film_details,
            "related_movies": related_data
        }, status=status.HTTP_200_OK)


#
from django.db.models import F
class RecordFilmViewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        viewer = request.user
        film_id = request.data.get("film_id")

        try:
            film = Film.objects.get(id=film_id)
        except Film.DoesNotExist:
            return Response({"message": "Film not found"}, status=status.HTTP_404_NOT_FOUND)

        if film.filmmaker == viewer:
            return Response({"message": "Filmmakers cannot view their own films"})

        # increment total views
        film.total_views = F("total_views") + 1
        film.save(update_fields=["total_views"])
        film.refresh_from_db(fields=["total_views"])

        # record every play
        FilmPlayView.objects.create(film=film, viewer=viewer)

        # handle unique view
        obj, created = FilmView.objects.get_or_create(
            film=film,
            viewer=viewer,
            defaults={"watch_time": 0}
        )
        if created:
            film.unique_views = F("unique_views") + 1
            film.save(update_fields=["unique_views"])
            film.refresh_from_db(fields=["unique_views"])

        return Response({
            "message": "View recorded",
            "unique_views": film.unique_views,
            "total_views": film.total_views
        }, status=status.HTTP_201_CREATED)


    
#
class RecordWatchTimeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        viewer = request.user
        film_id = request.data.get("film_id")
        watch_time = int(request.data.get("watch_time", 0))

        try:
            film = Film.objects.get(id=film_id)
        except Film.DoesNotExist:
            return Response({"message": "Film not found"}, status=status.HTTP_404_NOT_FOUND)

        if film.filmmaker == viewer:
            return Response({"message": "Filmmakers cannot watch their own films"}, status=status.HTTP_400_BAD_REQUEST)

        # Increment total watch time on Film
        film.total_watch_time = F("total_watch_time") + watch_time
        film.save(update_fields=["total_watch_time"])
        film.refresh_from_db(fields=["total_watch_time"])

        # Update FilmView for this viewer and film (latest entry)
        last_film_view = FilmView.objects.filter(film=film, viewer=viewer).order_by('-viewed_at').first()
        if last_film_view:
            # Add to total watch_time
            last_film_view.watch_time = F("watch_time") + watch_time
            # Update current session watch time
            last_film_view.current_watch_time = watch_time
            last_film_view.save(update_fields=["watch_time", "current_watch_time"])
        else:
            # If no FilmView exists, create one
            FilmView.objects.create(film=film, viewer=viewer, watch_time=watch_time, current_watch_time=watch_time)

        # Update FilmPlayView for this viewer and film (latest entry)
        last_play_view = FilmPlayView.objects.filter(film=film, viewer=viewer).order_by('-viewed_at').first()
        if last_play_view:
            last_play_view.watch_time = F("watch_time") + watch_time
            last_play_view.save(update_fields=["watch_time"])
        else:
            # If no FilmPlayView exists, create one
            FilmPlayView.objects.create(film=film, viewer=viewer, watch_time=watch_time)

        return Response({
            "message": "Watch time recorded",
            "total_watch_time": film.total_watch_time
        }, status=status.HTTP_200_OK)


#
class TrendingFilmsView(APIView):
    def get(self, request):
        # Get top trending published films by views
        trending_films = Film.objects.filter(status="PUBLISHED").order_by('-unique_views')[:10]

        trending_data = [
            {
                "id": f.id,
                # "filmmaker": str(f.filmmaker),
                "title": f.title,
                "slug":f.slug,
                "year": f.year,
                "logline": f.logline,
                "film_type": f.get_film_type_display(),
                "genre": [g.name for g in f.genre.all()] if hasattr(f.genre, "all") else f.genre,
                # "status": f.status,
                "buy_price": f.buy_price,
                "rent_price": f.rent_price,
                # "unique_views": f.unique_views,
                # "total_earning": f.total_earning,
                "thumbnail": f.thumbnail.url if f.thumbnail else None,
                "trailer_hls_url": f.trailer_hls_url,
                # "release_date": f.created_at.date(),
            }
            for f in trending_films
        ]

        return Response({
            "status": "success",
            "message": "Trending films fetched successfully",
            "data": trending_data
        })


class LatestFilmsView(APIView):
    def get(self, request):
        # Get latest published films by creation date
        latest_films = Film.objects.filter(status="PUBLISHED").order_by('-created_at')[:10]

        latest_data = [
            {
                "id": f.id,
                # "filmmaker": str(f.filmmaker),
                "title": f.title,
                "slug":f.slug,
                "year": f.year,
                "logline": f.logline,
                "film_type": f.get_film_type_display(),
                "genre": [g.name for g in f.genre.all()] if hasattr(f.genre, "all") else f.genre,
                # "status": f.status,
                "buy_price": f.buy_price,
                "rent_price": f.rent_price,
                # "unique_views": f.unique_views,
                # "total_earning": f.total_earning,
                "thumbnail": f.thumbnail.url if f.thumbnail else None,
                "trailer_hls_url": f.trailer_hls_url,
                # "release_date": f.created_at.date(),
            }
            for f in latest_films
        ]

        return Response({
            "status": "success",
            "message": "Latest films fetched successfully",
            "data": latest_data
        })




# ---------------------------
# option A
# ---------------------------

# from django.db.models import Q
# class MyTitlesView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         user = request.user
#         my_titles = Film.objects.filter(filmmaker=user)

#         # ---- Stats ----
#         stats = {
#             "total_films": my_titles.count(),
#             "published_films": my_titles.filter(status__iexact="published").count(),
#             "total_views": my_titles.aggregate(Sum("total_views"))["total_views__sum"] or 0,
#             "total_earning": my_titles.aggregate(Sum("total_earning"))["total_earning__sum"] or 0,
#         }

#         # ---- Filters ----
#         status_param = request.GET.get("status")
#         if status_param:
#             my_titles = my_titles.filter(status__iexact=status_param)

#         # ---- Search ----
#         search_param = request.GET.get("search")
#         if search_param:
#             my_titles = my_titles.filter(Q(title__icontains=search_param))


#         data = [
#             {
#                 "title": t.title,
#                 "status": t.get_status_display(),
#                 "film_type": t.get_film_type_display(),
#                 "views": t.total_views,
#                 "total_earning": t.total_earning
#             }
#             for t in my_titles
#         ]
        
#         return Response({
#             "status": "success",
#             "message": "My titles fetched successfully",
#             "stats": stats,
#             "data": data
#         })


# Pagination
from rest_framework.pagination import PageNumberPagination
class MyPagination(PageNumberPagination):
    page_size = 10                   # default items per page
    page_size_query_param = "page_size"  # frontend can set ?page_size=20
    max_page_size = 100

from django.db.models import Q
class MyTitlesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        # print(user)
        my_titles = Film.objects.filter(filmmaker=user).order_by("-created_at")

        # ---- Stats ----
        stats = {
            "total_films": my_titles.count(),
            "published_films": my_titles.filter(status__iexact="published").count(),
            "total_views": my_titles.aggregate(Sum("total_views"))["total_views__sum"] or 0,
            "total_earning": my_titles.aggregate(Sum("total_earning"))["total_earning__sum"] or 0,
        }

        # ---- Filters ----
        status_param = request.GET.get("status")

        if status_param:
            my_titles = my_titles.filter(status__iexact=status_param)

        # ---- Search ----
        search_param = request.GET.get("search")
        if search_param:
            my_titles = my_titles.filter(Q(title__icontains=search_param))

        # ---- Pagination ----
        paginator = MyPagination()
        result_page = paginator.paginate_queryset(my_titles, request)

        data = [
            {
                "title": t.title,
                "status": t.get_status_display(),
                "film_type": t.get_film_type_display(),
                "views": t.total_views,
                "total_earning": t.total_earning
            }
            for t in result_page
        ]
        
        return paginator.get_paginated_response({
            "status": "success",
            "message": "My titles fetched successfully",
            "stats": stats,
            "data": data
        })
    

# ---------------------------
# option B
# ---------------------------

# class MyTitlesView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         filmmaker = request.user
#         my_titles = Film.objects.filter(filmmaker=filmmaker)

#         data = []  # initialize the list outside the loop
#         for t in my_titles:
#             data.append({
#                 "title": t.title,
#                 "status": t.get_status_display(),      # human-readable label
#                 "film_type": t.get_film_type_display(),# human-readable label
#                 "views": t.unique_views,
#                 "total_earning": t.total_earning
#             })

#         return Response({
#             "status": "success",
#             "message": "My titles fetched successfully",
#             "data": data
#         })


class GenreListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        genres = Genre.objects.all().order_by("name")
        serializer = GenreSerializer(genres, many=True)

        return Response({
            "status": "success",
            "message": "Genres fetched successfully",
            "data": serializer.data
        })
    

#
class MyTitlesAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        
        film_id = request.data.get("film_id")
        
        film = Film.objects.filter(id=film_id).first()
        if not film:
            return Response({"message": "Film not found"}, status=404)
        
        today = date.today()

        # ---- 1. Totals from Film table ----
        total_views = film.total_views
        unique_viewers = film.unique_views
        total_earning = film.total_earning
        total_watch_time = film.total_watch_time

        # ---- 2. Daily Views (last 7 days) ----
        daily_views = []
        for i in range(7):
            day = today - timedelta(days=i)
            day_views = FilmPlayView.objects.filter(
                film=film,
                viewed_at__date=day
            ).count()
            daily_views.append({
                "date": day.strftime("%Y-%m-%d"),
                "views": day_views
            })
        daily_views.reverse()  # so oldest day is first

        # ---- 3. Weekly Earnings (last 7 weeks) ----
        weekly_earnings = []
        for i in range(7):
            week_start = today - timedelta(days=today.weekday() + i * 7)
            week_end = week_start + timedelta(days=6)
            week_earning = Transaction.objects.filter(
                film=film,
                tx_type__in=["purchase", "rent"],
                created_at__date__gte=week_start,
                created_at__date__lte=week_end
            ).aggregate(total=Sum("amount"))["total"] or 0
            weekly_earnings.append({
                "week_start": week_start.strftime("%Y-%m-%d"),
                "week_end": week_end.strftime("%Y-%m-%d"),
                "earning": float(week_earning)
            })
        weekly_earnings.reverse()  # so oldest week is first

        # ---- 4. Average Watch Time per view ----
        average_watch_time = total_watch_time / total_views if total_views else 0

        # ---- 5. Revenue Breakdown ----
        total_buy_earning = film.total_buy_earning
        total_rent_earning = film.total_rent_earning

        return Response({
            "film": film.title,
            "total_views": total_views,
            "unique_viewers": unique_viewers,
            "total_earning": float(total_earning),
            "daily_views": daily_views,
            "weekly_earnings": weekly_earnings,
            "average_watch_time_seconds": round(average_watch_time, 2),
            "total_buy_earning": float(total_buy_earning),
            "total_rent_earning": float(total_rent_earning)
        })


# -------------------------------------M.Alom----------------------------------
# Search Api
class GlobalSearchListView(APIView):
    def get(self, request):
        search_param = request.GET.get("search", "").strip()

        # Only search published films
        films_qs = Film.objects.filter(
            Q(title__icontains=search_param),
            status__iexact="published"
        )[:10]


        if films_qs.exists():
            data = [
                {
                    "id": film.id,
                    "title": film.title,
                }
                for film in films_qs
            ]
            return Response({
                "status": "success",
                "message": "Search films fetched successfully",
                "data": data,
            })
        else:
            return Response({
                "status": "success",
                "message": "No films found matching your search",
                "data": [],
            })


# -------------------------------------M.Alom----------------------------------
# My Library
from .models import MyFilms
from django.utils import timezone

class MyLibraryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        now = timezone.now()

        # ---- Auto-expire rentals ----
        MyFilms.objects.filter(
            user=user, access_type="Rent", end_date__lt=now, status="active"
        ).update(status="expired")

        my_library = MyFilms.objects.filter(user=user, status__iexact="active").order_by("-start_date")

        # ---- Stats ---- (only active)
        stats = {
            "total_buy": my_library.filter(access_type__iexact="Buy", status__iexact="active").count(),
            "total_rent": my_library.filter(access_type__iexact="Rent", status__iexact="active").count(),
        }

        # ---- Filters ----
        access_type_param = request.GET.get("access_type")
        if access_type_param:
            my_library = my_library.filter(access_type__iexact=access_type_param)

        # ---- Search ----
        search_param = request.GET.get("search")
        if search_param:
            my_library = my_library.filter(film__title__icontains=search_param)

        # ---- Pagination ----
        paginator = MyPagination()
        result_page = paginator.paginate_queryset(my_library, request)

        data = []
        for t in result_page:
            # Get last watched record for this user & film
            last_film_view = FilmView.objects.filter(film=t.film, viewer=user).first()
            current_watch_time = last_film_view.current_watch_time if last_film_view else 0

            full_duration = t.film.full_film_duration or 1  # avoid division by zero
            progress_percent = round((current_watch_time / full_duration) * 100, 2)
            # cap at 100%
            if progress_percent > 100:
                progress_percent = 100.0

            data.append({
                "film_id": t.film.id,
                "title": t.film.title,
                "film_type": t.film.get_film_type_display(),
                "full_film_duration": t.film.full_film_duration,
                "access_type": "Purchase" if t.access_type == "Buy" else "Rented",
                "status": t.status,
                "expiry_time": t.end_date if t.access_type == "Rent" else None,
                "thumbnail": t.film.thumbnail.url if t.film.thumbnail else None,
                "film_hls_url": None if t.status == "Expired" else t.film.film_hls_url,
                "watch_progress": progress_percent,
                "current_watch_time":current_watch_time
            })

        # return paginator.get_paginated_response({
        #     "status": "success",
        #     "message": "My titles fetched successfully",
        #     "stats": stats,
        #     "data": data
        # })
        
        return Response({
            "count": paginator.page.paginator.count,
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link(),
            "status": "success",
            "message": "My titles fetched successfully",
            "stats": stats,
            "data": data
        })
