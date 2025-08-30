from django.contrib import admin
from .models import Film, Genre, FilmView,FilmPlayView, MyFilms

class FilmAdmin(admin.ModelAdmin):
    list_display = ('id','title', 'year', 'status', 'created_at', 'updated_at', 'filmmaker')
    search_fields = ('title', 'filmmaker__email')
    list_filter = ('status', 'year', 'film_type', 'genre')

class GenreAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

class FilmViewAdmin(admin.ModelAdmin):
    list_display =('film', 'viewer')

class FilmPlayViewAdmin(admin.ModelAdmin):
    list_display =('id', 'film', 'viewer')

class MyFilmsAdmin(admin.ModelAdmin):
    list_display =('user', 'film', 'access_type', 'start_date', 'end_date')

# Register models in the admin interface
admin.site.register(Film, FilmAdmin)
admin.site.register(Genre, GenreAdmin)
admin.site.register(FilmView, FilmViewAdmin)
admin.site.register(FilmPlayView, FilmPlayViewAdmin)
admin.site.register(MyFilms, MyFilmsAdmin)
