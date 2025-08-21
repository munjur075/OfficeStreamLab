from django.urls import path
from . import views
from .views import *
# from .webhook import *

urlpatterns = [

    # path('create_checkout/', buy_subscription.as_view(), name='strip_payment'),
    # path('webhook/', StripeWebhookAPIView.as_view(), name='stripe_webhook'),
    # path('success/', views.success, name='success'),
    # path('cancel/', views.cancel, name='cancel'),
]
