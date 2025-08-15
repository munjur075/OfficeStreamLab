from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.FilmUploadView.as_view(), name='film_upload'),
    path('cloudinary-webhook/', views.cloudinary_webhook, name='cloudinary_webhook'),
]
