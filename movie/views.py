from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .models import Film, Genre
from .serializers import FilmSerializer
import tempfile, os, json
from cloudinary.uploader import upload as cloud_upload
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

class FilmUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        required_fields = ["title", "year", "logline", "film_type", "rent_price", "buy_price", "genre"]
        for field in required_fields:
            if field not in request.data or not request.data[field]:
                return Response({"error": f"Missing required field: {field}"}, status=status.HTTP_400_BAD_REQUEST)

        required_files = ["thumbnail", "trailer", "full_film"]
        for f in required_files:
            if f not in request.FILES:
                return Response({"error": f"Missing required file: {f}"}, status=status.HTTP_400_BAD_REQUEST)

        # Handle genres
        genres_input = request.data.get("genre")
        try:
            if isinstance(genres_input, str):
                genres_input = json.loads(genres_input)
        except json.JSONDecodeError:
            genres_input = [genres_input]

        if not isinstance(genres_input, list) or len(genres_input) == 0:
            return Response({"error": "At least one genre is required."}, status=status.HTTP_400_BAD_REQUEST)

        genres_input_normalized = [g.capitalize() for g in genres_input]
        invalid_genres = [g for g in genres_input_normalized if not Genre.objects.filter(name=g).exists()]
        if invalid_genres:
            return Response({"error": f"Invalid genre(s): {', '.join(invalid_genres)}"}, status=status.HTTP_400_BAD_REQUEST)

        def save_temp_file(uploaded_file):
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            for chunk in uploaded_file.chunks():
                tmp.write(chunk)
            tmp.close()
            return tmp.name

        try:
            # Upload thumbnail
            thumb_path = save_temp_file(request.FILES['thumbnail'])
            thumb_result = cloud_upload(file=thumb_path, folder=f"thumbnails")
            thumbnail_url = thumb_result.get("secure_url")
            os.remove(thumb_path)

            # Upload trailer
            trailer_path = save_temp_file(request.FILES['trailer'])
            trailer_id, trailer_duration, trailer_hls = Film.upload_video_with_hls(trailer_path, folder=f"trailers")
            os.remove(trailer_path)

            # Upload full film
            film_path = save_temp_file(request.FILES['full_film'])
            film_id, film_duration, film_hls = Film.upload_video_with_hls(film_path, folder=f"full_films")
            os.remove(film_path)
        except Exception as e:
            return Response({"error": f"File upload failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        film_data = {
            "title": request.data.get("title"),
            "year": request.data.get("year"),
            "logline": request.data.get("logline"),
            "film_type": request.data.get("film_type"),
            "rent_price": request.data.get("rent_price"),
            "buy_price": request.data.get("buy_price"),
            "thumbnail": thumbnail_url,
            "trailer": trailer_id,
            "trailer_hls_url": trailer_hls or "",
            "trailer_duration_s": trailer_duration,
            "full_film": film_id,
            "film_hls_url": film_hls or "",
            "film_duration_s": film_duration
        }

        serializer = FilmSerializer(data=film_data, context={"request": request})
        if serializer.is_valid():
            film = serializer.save()
            genre_objs = Genre.objects.filter(name__in=genres_input_normalized)
            film.genre.set(genre_objs)
            film.save()
            return Response(FilmSerializer(film).data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Cloudinary Webhook
@csrf_exempt
def cloudinary_webhook(request):
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    public_id = payload.get("public_id")
    resource_type = payload.get("resource_type")
    eager = payload.get("eager", [])

    if not public_id or resource_type != "video":
        return JsonResponse({"error": "Invalid payload"}, status=400)

    try:
        film = Film.objects.get(trailer=public_id)
        if eager:
            film.trailer_hls_url = eager[0].get("secure_url", "")
            film.save()
        return JsonResponse({"status": "trailer updated"})
    except Film.DoesNotExist:
        try:
            film = Film.objects.get(full_film=public_id)
            if eager:
                film.film_hls_url = eager[0].get("secure_url", "")
                film.save()
            return JsonResponse({"status": "full film updated"})
        except Film.DoesNotExist:
            return JsonResponse({"error": "Film not found"}, status=404)
