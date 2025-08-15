from rest_framework import serializers
from .models import Film, Genre

class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ["name"]  # Return names only

class FilmSerializer(serializers.ModelSerializer):
    genres = GenreSerializer(many=True, read_only=True)
    trailer_hls_url = serializers.CharField(read_only=True, allow_blank=True)
    film_hls_url = serializers.CharField(read_only=True, allow_blank=True)
    filmmaker = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Film
        fields = [
            "id",
            "title",
            "year",
            "logline",
            "film_type",
            "genres",
            "thumbnail",
            "trailer",
            "trailer_hls_url",
            "trailer_duration_s",
            "full_film",
            "film_hls_url",
            "film_duration_s",
            "rent_price",
            "buy_price",
            "rental_hours",
            "currency",
            "status",
            "created_at",
            "updated_at",
            "views",
            "total_earning",
            "filmmaker"
        ]
