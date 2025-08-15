from django.contrib import admin
from .models import Film, Genre

@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ["id", "name"]

@admin.register(Film)
class FilmAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "filmmaker", "film_type", "status", "created_at"]
    list_filter = ["film_type", "status"]
    search_fields = ["title", "filmmaker__email"]
