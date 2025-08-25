# subscriptions/urls.py
from django.urls import path
from .views import CreateCheckoutSessionView, checkout_success, checkout_cancel, PaypalCheckOutView, PaymentSuccessful, PaymentFailed
from .webhook import StripeWebhookAPIView

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
    path("paypal/checkout/", PaypalCheckOutView.as_view(), name="paypal_checkout"),
    path("paypal-checkout-success/", PaymentSuccessful, name="paypal-checkout-success"),
    path("paypal-checkout-failed/", PaymentFailed, name="paypal-checkout-failed"),
]