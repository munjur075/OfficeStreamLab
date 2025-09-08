from django.urls import path
from .views import UserManagementView

urlpatterns = [
    path('manage-users', UserManagementView.as_view(), name='manage_users'),
]
