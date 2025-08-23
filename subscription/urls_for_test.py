# from django.urls import path
# from . import views
# from .views import *
# from .webhook import *

# urlpatterns = [

#     # path('create_checkout/', buy_subscription.as_view(), name='strip_payment'),
#     # path('webhook/', StripeWebhookAPIView.as_view(), name='stripe_webhook'),
#     # path('success/', views.success, name='success'),
#     # path('cancel/', views.cancel, name='cancel'),
# ]

from django.urls import path
from . import views
from . import webhook

app_name = "subscription"   # <-- FIXED

urlpatterns = [
    # Checkout flow
    path("create_checkout_session/", views.CreateCheckoutSessionView.as_view(), name="create_checkout_session"),
    path("checkout_success/", views.checkout_success, name="checkout_success"),
    path("checkout_cancel/", views.checkout_cancel, name="checkout_cancel"),

    # Stripe webhook endpoint
    path("webhook/", webhook.stripe_webhook, name="stripe_webhook"),
]