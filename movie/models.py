from django.db import models
from django.utils.translation import gettext_lazy as _
from accounts.models import User
import shortuuid
from cloudinary.models import CloudinaryField
from cloudinary import uploader
from django.utils.text import slugify
from django.utils import timezone
from datetime import timedelta

def generate_short_uuid() -> str:
    return shortuuid.uuid()[:10]

class FilmStatus(models.TextChoices):
    REVIEW = "REVIEW", _("Under Review")
    PUBLISHED = "PUBLISHED", _("Published")
    REJECTED = "REJECTED", _("Rejected")


class FilmType(models.TextChoices):
    MOVIE = "MOVIE", _("Movie")
    DRAMA = "DRAMA", _("Drama")
    SHORT = "SHORT", _("Short Film")
    DOCUMENTARY = "DOCUMENTARY", _("Documentary")
    SERIES = "SERIES", _("Series")

    
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
    slug = models.SlugField(max_length=255, unique=True, editable=True, blank=True)  # ✅ auto movie_id
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    logline = models.CharField(max_length=280, blank=True)
    film_type = models.CharField(max_length=20, choices=FilmType.choices)
    genre = models.ManyToManyField(Genre, blank=True)

    thumbnail = CloudinaryField("image", folder="thumbnails", blank=True, null=True)
    trailer = CloudinaryField(resource_type="video", folder="trailers", blank=True, null=True)
    full_film = CloudinaryField(resource_type="video", folder="full_films", blank=True, null=True)

    trailer_public_id = models.CharField(max_length=255, blank=True, null=True)
    full_film_public_id = models.CharField(max_length=255, blank=True, null=True)


    status = models.CharField(max_length=12, choices=FilmStatus.choices, default=FilmStatus.REVIEW)
    currency = models.CharField(max_length=3, default="USD")
    rent_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    rental_hours = models.PositiveIntegerField(default=48)
    buy_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    full_film_duration = models.PositiveIntegerField(default=0)  # Duration in seconds

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    unique_views = models.PositiveIntegerField(default=0)   # distinct viewers
    total_views = models.PositiveIntegerField(default=0)    # every play
    total_earning = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Fields for multi-resolution HLS URLs
    trailer_hls_url = models.URLField(blank=True, null=True)
    film_hls_url = models.URLField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
    
    def save(self, *args, **kwargs):
        if not self.slug or (self.pk and Film.objects.filter(pk=self.pk, title=self.title).exists() is False):
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Film.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


    def __str__(self):
        return f"{self.title} ({self.year}) - {self.filmmaker.email}"
    


# Track unique views per Flims
class FilmView(models.Model):
    film = models.ForeignKey(Film, on_delete=models.CASCADE, related_name='views')
    viewer = models.ForeignKey(User, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)
    watched_seconds = models.PositiveIntegerField(default=0)  # new field to track watch time

    #

    class Meta:
        unique_together = ('film', 'viewer')  # ensures one record per user per film
        ordering = ['-viewed_at']

    def __str__(self):
        return f"{self.viewer.email} viewed {self.film.title}"



#
# -------------------- FILMS (BUY / RENT) --------------------
class FilmAccess(models.Model):
    """Tracks user access to films (buy = lifetime, rent = temporary)!"""

    ACCESS_TYPE = [
        ("Buy", "Lifetime"),
        ("Rent", "Temporary"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="film_access")
    film = models.ForeignKey(Film, on_delete=models.CASCADE, related_name="access")
    access_type = models.CharField(max_length=10, choices=ACCESS_TYPE)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Film Access"
        verbose_name_plural = "Film Accesses"
        unique_together = ("user", "film", "access_type")

    def save(self, *args, **kwargs):
        if self.access_type == "Rent" and not self.end_date:
            self.end_date = self.start_date + timedelta(days=self.film.rental_hours)
        super().save(*args, **kwargs)

    @property
    def is_active(self):
        if self.access_type == "Buy":
            return True
        return self.end_date and self.end_date >= timezone.now()

    def __str__(self):
        return f"{self.user} - {self.film.title} ({self.access_type})"

