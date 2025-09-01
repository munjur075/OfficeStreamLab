from django.urls import path
from .views import MyReelBuxView
urlpatterns = [

    # ReelBux
    path("balance/", MyReelBuxView.as_view(), name="balance"),
]
