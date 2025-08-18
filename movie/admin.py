from django.contrib import admin
from .models import Film, Genre

class FilmAdmin(admin.ModelAdmin):
    list_display = ('id','title', 'year', 'status', 'created_at', 'updated_at', 'filmmaker')
    search_fields = ('title', 'filmmaker__email')
    list_filter = ('status', 'year', 'film_type', 'genre')

class GenreAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

# Register models in the admin interface
admin.site.register(Film, FilmAdmin)
admin.site.register(Genre, GenreAdmin)
