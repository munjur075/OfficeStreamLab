
from django.urls import path
from .views import CreateCheckoutSessionView, stripe_checkout_success_view, stripe_checkout_cancel_view
from .stripe_webhook_for_subscriptions import StripeWebhookSubscriptionView
from .stripe_webhook_for_add_funds import StripeWebhookAddFundsView
from .paypal_for_subscriptions import CreatePaypalCheckoutView, ExecutePaypalPaymentView, paypal_cancel_view
from .reelbux_for_subscriptions import CreateReelBuxCheckoutView
from .stripe_add_funds import CreateAddFundsCheckoutSessionView, stripe_add_funds_checkout_success_view, stripe_add_funds_checkout_cancel_view
from .paypal_for_add_funds import*

app_name = "subscription"

urlpatterns = [
    # ================== STRIPE ==================
    # Checkout session (subscriptions)
    path("stripe/create-checkout-session/", CreateCheckoutSessionView.as_view(), name="stripe_create_checkout_session"),
    path("stripe/checkout-success/", stripe_checkout_success_view, name="stripe_checkout_success"),
    path("stripe/checkout-cancel/", stripe_checkout_cancel_view, name="stripe_checkout_cancel"),

    # Webhooks
    path("stripe/webhook/subscription/", StripeWebhookSubscriptionView.as_view(), name="stripe_subscription_webhook"),
    path("stripe/webhook/add-funds/", StripeWebhookAddFundsView.as_view(), name="stripe_add_funds_webhook"),

    # Add funds (wallet top-up)
    path("stripe/create-add-funds-checkout-session/", CreateAddFundsCheckoutSessionView.as_view(), name="stripe_create_add_funds_checkout_session"),
    path("stripe/checkout-add-funds-success/", stripe_add_funds_checkout_success_view, name="stripe_add_funds_checkout_success"),
    path("stripe/checkout-add-funds-cancel/", stripe_add_funds_checkout_cancel_view, name="stripe_add_funds_checkout_cancel"),

    # ================== PAYPAL ==================
    # (subscriptions)
    path("paypal/checkout-create/", CreatePaypalCheckoutView.as_view(), name="paypal_create_checkout"),
    path("paypal/execute/", ExecutePaypalPaymentView.as_view(), name="paypal_execute"),
    path("paypal/cancel/", paypal_cancel_view, name="paypal_cancel"),

    # Add funds (wallet top-up)
    path("paypal/create-addfunds-checkout/", CreatePaypalAddFundsView.as_view(), name="paypal_create_addfunds_checkout"),
    path("paypal/addfunds-execute/", ExecutePaypalAddFundsView.as_view(), name="paypal_addfunds_execute"),
    path("paypal/addfunds-cancel/", paypal_addfunds_cancel_view, name="paypal_addfunds_cancel"),

    # ================== REELBUX ==================
    path("reelbux/checkout-create/", CreateReelBuxCheckoutView.as_view(), name="reelbux_checkout_create"),
]
