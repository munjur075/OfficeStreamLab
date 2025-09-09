from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework import status
from django.db.models import Q, Sum

from accounts.models import User
from movie.models import Film
from .serializers import ManageUserSerializer


class UserManagementView(APIView):
    permission_classes = [IsAdminUser]  # Only admins can access

    # GET: list all non-admin users, with optional search
    def get(self, request):
        search_query = request.GET.get("search", "").strip()

        # Exclude admin
        users = User.objects.exclude(role="admin")

        # If search query provided, filter
        if search_query:
            users = users.filter(
                Q(full_name__icontains=search_query) | Q(email__icontains=search_query)
            )

        total_users = users.count()
        serializer = ManageUserSerializer(users, many=True)

        return Response({
            "status": "success",
            "message": "Users fetched successfully",
            "total_users": total_users,
            "users": serializer.data
        })

    # DELETE: remove a user by ID (only non-admin users)
    def delete(self, request):
        user_id_param = request.GET.get("user_id", "").strip()

        # user_id_param = request.data.get("user_id").strip()
        if not user_id_param:
            return Response({
                "status": "error",
                "message": "User ID is required"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Exclude admin to prevent accidental deletion
            user = User.objects.exclude(role="admin").get(id=user_id_param)
            user.delete()
            return Response({
                "status": "success",
                "message": f"User {user.full_name} deleted successfully"
            })
        except User.DoesNotExist:
            return Response({
                "status": "error",
                "message": "User not found"
            }, status=status.HTTP_404_NOT_FOUND)
        


# =========================== Films ============================
class AdminFilmsView(APIView):
    permission_classes = [IsAdminUser]  # Only admins can access

    def get(self, request):
        films = Film.objects.all()

        stats = {
            "total_films": films.count(),
            "total_buy": films.aggregate(total=Sum("total_buy_earning"))["total"] or 0,
            "total_rent": films.aggregate(total=Sum("total_rent_earning"))["total"] or 0,
        }

        # Get only under review films
        under_review_films = Film.objects.filter(status="REVIEW")
        review_films = [
            {
                "id": f.id,
                # "filmmaker": str(f.filmmaker),
                "title": f.title,
                "film_type": f.get_film_type_display(),
                "thumbnail": f.thumbnail.url if f.thumbnail else None,
                "release_date": f.created_at.date(),
            }
            for f in under_review_films
        ]

        # Filter films where status is either "PUBLISHED" or "REJECTED"
        track_all_films = Film.objects.filter(status__in=["PUBLISHED", "REJECTED"])

        track_films = [
            {
                "id": f.id,
                "filmmaker": str(f.filmmaker),
                "title": f.title,
                "film_type": f.get_film_type_display(),
                "status": f.get_status_display(),
                "release_date": f.created_at.date(),
                "total_views": f.total_views,
                "total_earning": f.total_earning
            }
            for f in track_all_films
        ]

        return Response({
            "status": "success",
            "message": "Films fetched successfully",
            "stats": stats,
            "review_films": review_films,
            "track_all_films": track_films,
        })


    # # DELETE: Film
    # def delete(self, request):
    #     film_id_param = request.GET.get("film_id", "").strip()

    #     if not film_id_param:
    #         return Response({
    #             "status": "error",
    #             "message": "Film ID is required"
    #         }, status=status.HTTP_400_BAD_REQUEST)

    #     try:
    #         # Fetch the film
    #         film = Film.objects.get(id=film_id_param)
    #         title = film.title  # save before deleting
    #         film.delete()

    #         return Response({
    #             "status": "success",
    #             "message": f"Film '{title}' deleted successfully"
    #         })

    #     except Film.DoesNotExist:
    #         return Response({
    #             "status": "error",
    #             "message": "Film not found"
    #         }, status=status.HTTP_404_NOT_FOUND)
