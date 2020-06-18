from django.contrib import admin

# Register your models here.

from .models import Artist
from .models import Track
from .models import Genre
from .models import Playlist
from .models import TransitionType
from .models import TrackToTrack

#admin.site.register(Artist)
#admin.site.register(Track)
admin.site.register(Genre)
admin.site.register(Playlist)
admin.site.register(TrackToTrack)
admin.site.register(TransitionType)

#class TrackInline(admin.StackedInline):
class TrackInline(admin.TabularInline):
    model = Track
    extra = 1

#class TrackInline(admin.StackedInline):
class TrackToTrackInline(admin.TabularInline):
    model = TrackToTrack
    extra = 1
    fk_name = "track_source"

class TrackAdmin(admin.ModelAdmin):
    fieldsets = [
        (None,               {'fields': ['title', 'artist']}),
        ('Other information', {'fields': ['genre', 'bpm']}),
    ]
    inlines = [TrackToTrackInline]
    list_display = ('title', 'artist', 'genre', 'bpm', 'is_techno', 'was_added_recently')
    list_filter = ['genre']
    search_fields = ['title', 'artist__name']
    ordering = ['title']

class ArtistAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Say my name!',               {'fields': ['name']}),
    ]
    inlines = [TrackInline]

admin.site.register(Track, TrackAdmin)
admin.site.register(Artist, ArtistAdmin)