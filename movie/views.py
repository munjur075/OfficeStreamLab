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
from .serializers import FilmSerializer, FilmListSerializer


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
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
def cloudinary_webhook(request):
    """
    Updates HLS URLs and duration after Cloudinary finishes processing large videos.
    Ensures multi-resolution streaming works in production.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=400)

    try:
        payload = json.loads(request.body)
        print(payload)
        public_id = payload.get("public_id")
        resource_type = payload.get("resource_type")
        duration = payload.get("duration")

        film = None
        if Film.objects.filter(trailer_public_id=public_id).exists():
            film = Film.objects.get(trailer_public_id=public_id)
        elif Film.objects.filter(full_film_public_id=public_id).exists():
            film = Film.objects.get(full_film_public_id=public_id)

        if not film:
            return JsonResponse({"error": "Film not found"}, status=404)

        if resource_type == "video":
            if duration:
                film.full_film_duration = duration

            # Master HLS URL for adaptive streaming
            film.film_hls_url = f"https://res.cloudinary.com/{cloudinary.config().cloud_name}/video/upload/{public_id}.m3u8"

        film.save()
        return JsonResponse({"status": "success", "film_id": film.id})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


def film_detail(request, film_id):
    """
    Render film detail page with HLS video player
    """
    film = get_object_or_404(Film, id=film_id)
    return render(request, "movie/film_detail.html", {"film": film})

class AllFlimListView(APIView):
    """
    Returns a list of films with status 'published', newest first.
    """
    def get(self, request):
        films = Film.objects.filter(status__iexact='published').order_by('-created_at')
        print(films)  # Will show queryset in console
        serializer = FilmListSerializer(films, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class FilmDetailView(APIView):
    """
    Returns details of a specific film by its ID (only if review).
    """
    def get(self, request, film_id):
        # Get film with status 'published' (case-insensitive)
        film = get_object_or_404(Film, id=film_id, status__iexact='review')
        serializer = FilmSerializer(film)
        return Response(serializer.data, status=status.HTTP_200_OK)
    



from django.db import IntegrityError
class FilmPlayView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, film_id):
        user = request.user
        try:
            film = Film.objects.get(id=film_id)
        except Film.DoesNotExist:
            return Response({"error": "Film not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            FilmView.objects.create(film=film, user=user)
           
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

#
class TrendingFilmsView(APIView):
    def get(self, request):
        # Get top trending published films by views
        trending_films = Film.objects.filter(status="published").order_by('-views_count')[:10]

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
        latest_films = Film.objects.filter(status="published").order_by('-created_at')[:10]

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

    