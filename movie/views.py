import cloudinary
import cloudinary.uploader
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404, render
from rest_framework.permissions import IsAuthenticated
from .models import Film, Genre, FilmView
from .serializers import FilmSerializer, FilmListSerializer, GenreSerializer


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

# For HLS Testing by Frontend
def film_detail(request, film_id):
    """
    Render film detail page with HLS video player
    """
    film = get_object_or_404(Film, id=film_id)
    return render(request, "movie/film_detail.html", {"film": film})


    
class FilmDetailsView(APIView):
    """
    Returns details of a specific published film by its ID, 
    including related movies.
    """
    def get(self, request, film_id):
        
        # Fetch film with case-insensitive status check
        film = get_object_or_404(Film, id=film_id, status__iexact='published')

        # Build film details
        film_details = {
            "id": film.id,
            "filmmaker": str(film.filmmaker),
            "title": film.title,
            "slug":film.slug,
            "year": film.year,
            "logline": film.logline,
            "film_type": film.film_type,
            "genre": [g.name for g in film.genre.all()] if hasattr(film.genre, "all") else film.genre,
            "thumbnail": film.thumbnail.url if film.thumbnail else None,
            "status": film.status,
            "rent_price": film.rent_price,
            "rental_hours": film.rental_hours,
            "buy_price": film.buy_price,
            "full_film_duration": film.full_film_duration,
            "views_count": film.views_count,
            "total_earning": film.total_earning,
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
                "filmmaker": str(f.filmmaker),
                "title": f.title,
                "slug":film.slug,
                "year": f.year,
                "logline": f.logline,
                "film_type": f.film_type,
                "genre": [g.name for g in f.genre.all()] if hasattr(f.genre, "all") else f.genre,
                "thumbnail": f.thumbnail.url if f.thumbnail else None,
                "status": f.status,
                "rent_price": f.rent_price,
                "rental_hours": f.rental_hours,
                "buy_price": f.buy_price,
                "full_film_duration": f.full_film_duration,
                "views_count": f.views_count,
                "total_earning": f.total_earning,
                "trailer_hls_url": f.trailer_hls_url,
            }
            for f in related_films
        ]

        return Response({
            "status": "success",
            "message": "Film details fetched successfully",
            "data": {
                "film": film_details,
                "related_movies": related_data
            }
        }, status=status.HTTP_200_OK)



from django.db import IntegrityError
class FilmPlayView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, film_id):
        viewer = request.user
        print(viewer)
        try:
            film = Film.objects.get(id=film_id)
        except Film.DoesNotExist:
            return Response({"message": "Film not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            FilmView.objects.create(film=film, viewer=viewer)
           
            film.views_count += 1
            film.save()
            
        except IntegrityError:
            # already viewedpytho
            pass

        return Response({
            "message": "View recorded",
            "views_count": film.views_count
        })



#
class TrendingFilmsView(APIView):
    def get(self, request):
        # Get top trending published films by views
        trending_films = Film.objects.filter(status="PUBLISHED").order_by('-views_count')[:10]

        trending_data = [
            {
                "id": f.id,
                "title": f.title,
                "views": f.views_count,
                "release_date": f.created_at.date(),
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
                "title": f.title,
                "views": f.views_count,
                "release_date": f.created_at.date(),
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
class MyTitlesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        filmmaker = request.user
        my_titles = Film.objects.filter(filmmaker=filmmaker)

        data = [
            {
                "title": t.title,
                "status": t.get_status_display(),      # human-readable label
                "film_type": t.get_film_type_display(),# human-readable label
                "views": t.views_count,
                "total_earning": t.total_earning
            }
            for t in my_titles
        ]

        return Response({
            "status": "success",
            "message": "My titles fetched successfully",
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
#                 "views": t.views_count,
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