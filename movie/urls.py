from django.urls import path
from .views import FilmUploadView, cloudinary_webhook, FilmDetailsView, RecordFilmViewAPIView, RecordWatchTimeAPIView, TrendingFilmsView, LatestFilmsView, MyTitlesView, MyTitlesAnalyticsView, GenreListView, GlobalSearchListView, MyLibraryView
from .reelbux_for_film_purchase import *
from .reelbux_for_film_rented import *
from .paypal_for_film_purchase import *
from .paypal_for_film_rented import *
from .stripe_for_film_purchase import *
from .stripe_for_film_rented import *

app_name = "movie"

urlpatterns = [
    # film upload
    path("upload", FilmUploadView.as_view(), name="film_upload"),

    # URL to handle Cloudinary webhook notifications
    path("webhook/cloudinary", cloudinary_webhook, name='cloudinary_webhook'),

    # ----------- Extra ------------#
    path("views-count", RecordFilmViewAPIView.as_view(), name="views_count"),
    path("watch-time-count", RecordWatchTimeAPIView.as_view(), name="watch_time_count"),
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

    # My library
    path("my-library", MyLibraryView.as_view(), name="my_library"),

    # Genre list
    path("genre", GenreListView.as_view(), name="genre"),

    # ================== ReelBux ==================
    # payment (film purchase)
    path("reelbux/purchase", FilmPurchaseReelBuxView.as_view(), name="purchase"),

    # payment (film rented)
    path("reelbux/rented", FilmRentedReelBuxView.as_view(), name="rented"),

    # ================== PAYPAL ==================
    # payment (film purchase)
    path("paypal/create-purchase-checkout", CreatePaypalFilmPurchaseView.as_view(), name="paypal_create_purchase_checkout"),
    path("paypal/purchase-execute", ExecutePaypalFilmPurchaseView.as_view(), name="paypal_purchase_execute"),
    path("paypal/purchase-cancel", paypal_film_cancel_view, name="paypal_purchase_cancel"),

    # payment (film rented)
    path("paypal/create-rented-checkout", CreatePaypalFilmRentedView.as_view(), name="paypal_create_rented_checkout"),
    path("paypal/rented-execute", ExecutePaypalFilmRentedView.as_view(), name="paypal_rented_execute"),
    path("paypal/rented-cancel", paypal_film_rented_cancel_view, name="paypal_rented_cancel"),

    # ================== STRIPE ==================
    # webhook
    path("stripe/webhook/purchase", StripeWebhookPurchaseView.as_view(), name="stripe_purchase_webhook"),
    path("stripe/webhook/rented", StripeWebhookRentedView.as_view(), name="stripe_rented_webhook"),

    # Add funds (wallet top-up)
    path("stripe/create-purchase-checkout-session", CreateStripePurchaseCheckoutSessionView.as_view(), name="stripe_create_purchase_checkout_session"),
    path("stripe/checkout-purchase-success", stripe_purchase_checkout_success_view, name="stripe_purchase_checkout_success"),
    path("stripe/checkout-purchase-cancel", stripe_purchase_checkout_cancel_view, name="stripe_purchase_checkout_cancel"),

    # payment (film rented)
    path("stripe/create-rented-checkout-session", CreateStripeRentedCheckoutSessionView.as_view(), name="stripe_create_rented_checkout_session"),
    path("stripe/checkout-rented-success", stripe_rented_checkout_success_view, name="stripe_rented_checkout_success"),
    path("stripe/checkout-rented-cancel", stripe_rented_checkout_cancel_view, name="stripe_rented_checkout_cancel"),

]
