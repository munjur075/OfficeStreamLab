from rest_framework import serializers
from .models import Film

class FilmSerializer(serializers.ModelSerializer):
    genre = serializers.StringRelatedField(many=True)
    class Meta:
        model = Film
        fields = "__all__"
        read_only_fields = ("trailer_hls_url", "film_hls_url", "film_duration_s", "status", "views", "total_earning")


class FilmListSerializer(serializers.ModelSerializer):
    genre = serializers.StringRelatedField(many=True)
    class Meta:
        model = Film
        fields = "__all__"

