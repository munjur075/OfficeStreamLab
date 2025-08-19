from django.urls import path
from .views import FilmUploadView, cloudinary_webhook, film_detail, FilmDetailView, FilmPlayView,TrendingFilmsView, LatestFilmsView

urlpatterns = [
    # URL to handle film upload via FilmUploadView
    path('upload/', FilmUploadView.as_view(), name='film-upload'),

    # URL to handle Cloudinary webhook notifications
    path('webhook/cloudinary/', cloudinary_webhook, name='cloudinary-webhook'),
    path("film-detail/<str:film_id>/", film_detail, name="film_detail"),

    path("filmdetails/<str:film_id>/", FilmDetailView.as_view(), name="filmdetails"),
    path("views-count/<str:film_id>/", FilmPlayView.as_view(), name="views-count"),

    # trending-films
    path("trending/", TrendingFilmsView.as_view(), name="trending"),

    # latest-films
    path("latest/", LatestFilmsView.as_view(), name="latest"),
]
