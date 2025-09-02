from django.urls import path
from .views import FilmUploadView, cloudinary_webhook, FilmDetailsView, RecordFilmViewAPIView, RecordWatchTimeAPIView, TrendingFilmsView, LatestFilmsView, MyTitlesView, MyTitlesAnalyticsView, GenreListView, GlobalSearchListView

urlpatterns = [
    # film upload
    path('upload/', FilmUploadView.as_view(), name='film-upload'),

    # URL to handle Cloudinary webhook notifications
    path('webhook/cloudinary/', cloudinary_webhook, name='cloudinary-webhook'),

    # ----------- Extra ------------#
    path("views-count/", RecordFilmViewAPIView.as_view(), name="views_count"),
    path("watch-time-count/", RecordWatchTimeAPIView.as_view(), name="watch_time_count"),
    # ----------- End -------------#

    # trending, latest & film details
    path("trending", TrendingFilmsView.as_view(), name="trending"),
    path("latest", LatestFilmsView.as_view(), name="latest"),
    path("details", FilmDetailsView.as_view(), name="details"),

    # Search api
    path("search", GlobalSearchListView.as_view(), name="search"),

    # My titles
    path("my-titles", MyTitlesView.as_view(), name="my_titles"),
    path("my-titles/analytics", MyTitlesAnalyticsView.as_view(), name="my_titles_analytics"),

    # Genre list
    path("genre", GenreListView.as_view(), name="genre"),

]
