from rest_framework import serializers
from .models import Film, Genre

class FilmSerializer(serializers.ModelSerializer):
    genre = serializers.StringRelatedField(many=True)
    class Meta:
        model = Film
        fields = "__all__"
        read_only_fields = ("trailer_hls_url", "film_hls_url", "film_duration_s", "status", "ivews", "total_earning")


class FilmListSerializer(serializers.ModelSerializer):
    genre = serializers.StringRelatedField(many=True)
    class Meta:
        model = Film
        fields = "__all__"


# class FilmsDetailsSerializer(serializers.ModelSerializer):
#     genre = serializers.StringRelatedField(many=True)
#     class Meta:
#         model = Film
#         fields = "__all__"



class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ["id", "name"]
