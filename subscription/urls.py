# subscriptions/urls.py
from django.urls import path
from .views import CreateCheckoutSessionView, checkout_success, checkout_cancel
from .webhook import StripeWebhookAPIView
from .paypal import *

app_name = "subscription"

urlpatterns = [
    # Stripe checkout session
    path("create-checkout-session/", CreateCheckoutSessionView.as_view(), name="create_checkout_session"),

    # Checkout success/cancel redirects
    path("checkout-success/", checkout_success, name="checkout_success"),
    path("checkout-cancel/", checkout_cancel, name="checkout_cancel"),
    # Stripe webhook endpoint
    path("webhook/", StripeWebhookAPIView.as_view(), name="stripe_webhook"),

    # ---------- PayPal ----------
    path("paypal-checkcout-create/", CreatePaypalCheckoutView.as_view(), name="paypal_create"),
    path("paypal/execute/", ExecutePaypalPaymentView.as_view(), name="paypal_execute"),
    path("paypal/cancel/", paypal_cancel, name="paypal_cancel"),
]