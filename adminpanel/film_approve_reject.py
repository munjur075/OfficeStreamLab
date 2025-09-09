from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework import status
from movie.models import Film


class FilmApproveRejectView(APIView):
    """
    Admin API to approve or reject a film.
    Accepts `film_id` and `action` ("approve" or "reject") in request data.
    Case-insensitive for `action`.
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        film_id = request.data.get("film_id")
        action = request.data.get("action", "").strip().lower()  # Normalize input to lowercase

        # Validate input
        if not film_id or action not in ["approve", "reject"]:
            return Response({
                "status": "error",
                "message": "film_id and valid action ('approve' or 'reject') are required."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Fetch the film
        try:
            film = Film.objects.get(id=film_id)
        except Film.DoesNotExist:
            return Response({
                "status": "error",
                "message": "Film not found."
            }, status=status.HTTP_404_NOT_FOUND)

        # Update status
        if action == "approve":
            film.status = "PUBLISHED"
            msg = f"Film '{film.title}' has been approved."
        else:  # action == "reject"
            film.status = "REJECTED"
            msg = f"Film '{film.title}' has been rejected."

        film.save()

        return Response({
            "status": "success",
            "message": msg,
            "film_id": film.id,
            "new_status": film.get_status_display()
        }, status=status.HTTP_200_OK)
