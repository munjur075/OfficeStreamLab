from django.urls import path
from .views import FilmUploadView, cloudinary_webhook, film_detail, FilmDetailsView, RecordFilmViewAPIView, RecordWatchTimeAPIView, TrendingFilmsView, LatestFilmsView, MyTitlesView, GenreListView, FilmAnalyticsView

urlpatterns = [
    # film upload
    path('upload/', FilmUploadView.as_view(), name='film-upload'),

    # URL to handle Cloudinary webhook notifications
    path('webhook/cloudinary/', cloudinary_webhook, name='cloudinary-webhook'),

    # ----------- Extra ------------#
    path("film-detail/<str:film_id>/", film_detail, name="film_detail"),
    path("views-count/", RecordFilmViewAPIView.as_view(), name="views_count"),
    path("watch-time-count/", RecordWatchTimeAPIView.as_view(), name="watch_time_count"),
    # ----------- End -------------#

    # films details & related films
    path("details/<str:film_id>/", FilmDetailsView.as_view(), name="details"),

    # trending-films
    path("trending/", TrendingFilmsView.as_view(), name="trending"),

    # latest-films
    path("latest/", LatestFilmsView.as_view(), name="latest"),

    # my titles
    path("my-titles/", MyTitlesView.as_view(), name="my-titles"),

    # genre list
    path("genre/", GenreListView.as_view(), name="genre"),

    # Films Analytics
    path("analytics/", FilmAnalyticsView.as_view(), name="analytics"),
]
