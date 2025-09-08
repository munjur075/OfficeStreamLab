from django.urls import path
from .views import UserManagementView, AdminFilmsView

urlpatterns = [
    path('manage-users', UserManagementView.as_view(), name='manage_users'),
    path('films', AdminFilmsView.as_view(), name='films'),
]
