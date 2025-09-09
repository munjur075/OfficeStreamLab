from django.urls import path
from .views import UserManagementView, AdminFilmsView
from .film_delete import *

urlpatterns = [
    path('manage-users', UserManagementView.as_view(), name='manage_users'),
    path('films', AdminFilmsView.as_view(), name='films'),
    path('films-delete', FilmDeleteView.as_view(), name='films_delete'),
]
