from django.urls import path
from .views import FilmUploadView, cloudinary_webhook, FilmDetailsView, RecordFilmViewAPIView, RecordWatchTimeAPIView, TrendingFilmsView, LatestFilmsView, MyTitlesView, MyTitlesAnalyticsView, GenreListView, GlobalSearchListView, MyLibraryView
from .film_purchase_reelbux import FilmPurchaseReelBuxView
from .paypal_for_film_purchase import *
from .film_rented_paypal import *
from .film_purchase_stripe import *
# from .film_purchase_stripe_webhook import *

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

    # Film Purchase Using ReelBux
    path("reelbux/purchase", FilmPurchaseReelBuxView.as_view(), name="purchase"),

    # Genre list
    path("genre", GenreListView.as_view(), name="genre"),

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
    path("stripe/webhook/purchase", StripeWebhookPurchaseView.as_view(), name="stripe_purchase_webhook"),

    # Add funds (wallet top-up)
    path("stripe/create-purchase-checkout-session", CreateStripePurchaseCheckoutSessionView.as_view(), name="stripe_create_purchase_checkout_session"),
    path("stripe/checkout-purchase-success", stripe_purchase_checkout_success_view, name="stripe_purchase_checkout_success"),
    path("stripe/checkout-purchase-cancel", stripe_purchase_checkout_cancel_view, name="stripe_purchase_checkout_cancel"),

]
