from django.urls import path
from .views import MyDistroView
urlpatterns = [

    # # Distro
    path("balance", MyDistroView.as_view(), name="balance"),
]
