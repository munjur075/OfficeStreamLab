from django.urls import path
from .views import UserManagementView, AdminFilmsView
from .film_delete import *
from .film_approve_reject import *

urlpatterns = [
    path('manage-users', UserManagementView.as_view(), name='manage_users'),
    path('films', AdminFilmsView.as_view(), name='films'),
    path('films-delete', FilmDeleteView.as_view(), name='films_delete'),
    path('films-approve-reject', FilmApproveRejectView.as_view(), name='films_approve_reject'),
]
