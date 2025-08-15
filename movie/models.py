from django.db import models
from django.utils.translation import gettext_lazy as _
from accounts.models import User
import shortuuid
from cloudinary.models import CloudinaryField
from cloudinary import uploader

def generate_short_uuid() -> str:
    return shortuuid.uuid()[:10]

class FilmStatus(models.TextChoices):
    REVIEW = "review", _("In Review")
    PUBLISHED = "published", _("Published")
    REJECTED = "rejected", _("Rejected")

class FilmType(models.TextChoices):
    MOVIE = "movie", _("Movie")
    DRAMA = "drama", _("Drama")
    SHORT = "short", _("Short")
    DOCUMENTARY = "documentary", _("Documentary")
    SERIES = "series", _("Series")

class Genre(models.Model):
    name = models.CharField(max_length=60, unique=True)

    class Meta:
        verbose_name_plural = "Genres"
        ordering = ["name"]

    def __str__(self):
        return self.name

class Film(models.Model):
    id = models.CharField(primary_key=True, max_length=10, default=generate_short_uuid, editable=False, unique=True)
    filmmaker = models.ForeignKey(User, on_delete=models.CASCADE, related_name="films")
    title = models.CharField(max_length=200)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    logline = models.CharField(max_length=280, blank=True)
    film_type = models.CharField(max_length=20, choices=FilmType.choices)
    genre = models.ManyToManyField(Genre, blank=True)

    thumbnail = CloudinaryField("image", folder="thumbnails", blank=True, null=True)
    trailer = CloudinaryField(resource_type="video", folder="trailers", blank=True, null=True)
    trailer_hls_url = models.URLField(blank=True)
    trailer_duration_s = models.PositiveIntegerField(default=0)
    full_film = CloudinaryField(resource_type="video", folder="full_films", blank=True, null=True)
    film_hls_url = models.URLField(blank=True)
    film_duration_s = models.PositiveIntegerField(default=0)

    status = models.CharField(max_length=12, choices=FilmStatus.choices, default=FilmStatus.REVIEW)
    currency = models.CharField(max_length=3, default="USD")
    rent_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    rental_hours = models.PositiveIntegerField(default=48)
    buy_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    views = models.PositiveIntegerField(default=0)
    total_earning = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.year}) - {self.filmmaker.email}"

    @staticmethod
    def upload_video_with_hls(file_path: str, folder: str):
        """
        Upload a video to Cloudinary with multi-resolution & HLS playlist.
        Returns (public_id, duration_seconds, hls_url).
        """
        result = uploader.upload_large(
            file=file_path,
            resource_type="video",
            streaming_profile="multi_res",
            folder=folder,
            eager=[{"format": "m3u8"}]
        )
        public_id = result["public_id"]
        duration = int(result.get("duration", 0))
        hls_url = result.get("eager")[0]["secure_url"] if result.get("eager") else ""
        return public_id, duration, hls_url
