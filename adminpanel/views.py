from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework import status
from django.db.models import Q

from accounts.models import User
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
