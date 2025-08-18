from django.urls import path
from .views import FilmUploadView, cloudinary_webhook, film_detail

urlpatterns = [
    # URL to handle film upload via FilmUploadView
    path('upload/', FilmUploadView.as_view(), name='film-upload'),

    # URL to handle Cloudinary webhook notifications
    path('webhook/cloudinary/', cloudinary_webhook, name='cloudinary-webhook'),
    path("film-detail/<str:film_id>/", film_detail, name="film_detail"),
]
