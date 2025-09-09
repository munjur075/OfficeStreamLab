import cloudinary.uploader
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from movie.models import Film


class FilmDeleteView(APIView):
    """
    Delete a film and all its associated Cloudinary media:
    - Thumbnail
    - Trailer
    - Full film
    """
    def delete(self, request):
        film_id_param = request.GET.get("film_id", "").strip()
        if not film_id_param:
            return Response({"status": "error", "message": "Film ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            film = Film.objects.get(id=film_id_param)
            title = film.title

            # Delete thumbnail
            if getattr(film, "thumbnail_public_id", None):
                try:
                    cloudinary.uploader.destroy(film.thumbnail_public_id, resource_type="image")
                except Exception as e:
                    print(f"Cloudinary thumbnail delete error: {e}")

            # Delete trailer
            if getattr(film, "trailer_public_id", None):
                try:
                    cloudinary.uploader.destroy(film.trailer_public_id, resource_type="video")
                except Exception as e:
                    print(f"Cloudinary trailer delete error: {e}")

            # Delete full film
            if getattr(film, "full_film_public_id", None):
                try:
                    cloudinary.uploader.destroy(film.full_film_public_id, resource_type="video")
                except Exception as e:
                    print(f"Cloudinary full film delete error: {e}")

            # Delete DB record
            film.delete()

            return Response({"status": "success", "message": f"Film '{title}' and its media deleted successfully"})

        except Film.DoesNotExist:
            return Response({"status": "error", "message": "Film not found"}, status=status.HTTP_404_NOT_FOUND)

