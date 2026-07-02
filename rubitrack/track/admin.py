from django.contrib import admin



# Register your models here.
from .models import Artist, Track, Genre, Playlist, TransitionType, Transition, CurrentlyPlaying, Collection, Config, CuePoint


from django import forms

from django.utils.html import format_html

admin.site.register(Genre)
admin.site.register(Transition)
admin.site.register(TransitionType)
admin.site.register(CurrentlyPlaying)
admin.site.register(Collection)


# class TrackInline(admin.StackedInline):
class TrackInline(admin.TabularInline):
    model = Track
    extra = 1


# class TrackInline(admin.StackedInline):
class TransitionInlineSource(admin.TabularInline):
    model = Transition
    verbose_name_plural = "Transitions : What to play next?"
    extra = 1
    fk_name = "track_source"
    fields = (('track_destination', 'comment'),)
    widgets = {
        'comment': forms.Textarea(attrs={'rows': 2, 'cols': 2}),
    }


# class TrackInline(admin.StackedInline):
class TransitionInlineDestination(admin.TabularInline):
    model = Transition
    verbose_name_plural = "Previous Transitions - Tracks to play before"
    extra = 1
    fk_name = "track_destination"
    fields = (('track_source', 'comment'),)
    widgets = {
        'comment': forms.Textarea(attrs={'rows': 2, 'cols': 2}),
    }


# @admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['title', 'artist', 'genre']}),
        ('Notes', {'fields': ['ranking', 'comment', 'comment2']}),
        ('Details', {'fields': ['musical_key', 'bpm', 'bitrate', 'playcount', 'date_last_played']}),
    ]
    inlines = [TransitionInlineSource]
    list_display = ('title', 'artist', 'history_editing', 'genre', 'musical_key', 'ranking')
    list_filter = ['genre', 'musical_key', 'ranking']
    search_fields = ['title', 'artist__name']
    ordering = ['title']

    def history_editing(self, obj):
        return format_html("<a href='/track/history_editing/{url}'>{label} (All Transitions)</a>", url=obj.id, label=obj.title)

    history_editing.description = 'Edit Tansitions'

admin.site.register(Track, TrackAdmin)

class ArtistAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Say my name!', {'fields': ['name']}),
    ]
    inlines = [TrackInline]



admin.site.register(Artist, ArtistAdmin)


# custom track admin view
class CustomTrackTransition(Track):
    class Meta:
        proxy = True


# v2 for resize area
class TransitionForm(forms.ModelForm):
    comment = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3, 'cols': 15}))

    class Meta:
        model = Transition
        exclude = ('comment',)
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 2, 'cols': 2}),
        }


class CustomTrackTransitionAdmin(TrackAdmin):
    title = 'Add a new transition'
    fieldsets = None
    fields = (('title'),)
    inlines = [TransitionInlineSource, TransitionInlineDestination]


admin.site.register(CustomTrackTransition, CustomTrackTransitionAdmin)


class CustomPlaylistAdmin(admin.ModelAdmin):
    list_display = ['favourite_star', 'playlist_transitions', 'playlist_name_link']
    # list_display = ['name', 'id']
    search_fields = ['name']
    ordering = ['rank', '-id']  # Si même rank, trier par ID décroissant

    class Media:
        css = {
            'all': ('/static/css/playlist_admin.css',)
        }
        js = ('/static/js/playlist_admin.js',)

    def favourite_star(self, obj):
        """Display a clickable star to toggle favourite status"""
        from .models import Config
        config = Config.get_config()
        favourite_ids = [x.strip() for x in config.default_playlist_favourites.split(';') if x.strip()]
        is_favourite = str(obj.id) in favourite_ids

        star_icon = '★' if is_favourite else '☆'
        star_class = 'favourite-star-filled' if is_favourite else 'favourite-star-empty'

        return format_html(
            '<span class="favourite-star {}" data-playlist-id="{}" style="cursor: pointer; font-size: 20px; color: {};" title="Click to toggle favourite">{}</span>',
            star_class,
            obj.id,
            '#FFD700' if is_favourite else '#ccc',
            star_icon
        )

    favourite_star.short_description = '⭐'
    favourite_star.allow_tags = True

    def playlist_transitions(self, obj):
        return format_html(
            "<a href='/track/playlist_transitions/{url}'>{label} (All Transitions)</a>",
            url=obj.id,
            label=obj.name
        )
    playlist_transitions.description = 'Playlist Transitions'

    def playlist_name_link(self, obj):
        return format_html(
            "<a href='/admin/track/playlist/{}/change/'>{}</a>",
            obj.id,
            obj.name
        )
    playlist_name_link.description = 'Name'

admin.site.register(Playlist, CustomPlaylistAdmin)
# admin.site.register(Playlist)


@admin.register(Config)
class ConfigAdmin(admin.ModelAdmin):
    """Admin interface for Config model"""

    list_display = ['__str__', 'updated_at', 'updated_by']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Refresh Intervals', {
            'fields': ('refresh_interval_currently_playing_ms', 'refresh_interval_history_editing_ms'),
            'description': 'Configuration des intervalles de rafraîchissement des pages'
        }),
        ('Icecast & Playlists', {
            'fields': ('rubi_icecast_playlist_file', 'max_playlist_history_size', 'max_suggestions_auto_size'),
            'description': 'Configuration Icecast et gestion des playlists'
        }),
        ('Interface utilisateur', {
            'fields': ('max_title_length', 'max_artist_name_length'),
            'description': 'Paramètres d\'affichage de l\'interface'
        }),
        ('Base de données', {
            'fields': ('default_bpm', 'default_genre'),
            'description': 'Valeurs par défaut pour les nouveaux éléments'
        }),
        ('API Settings', {
            'fields': ('max_suggestions', 'max_playlist_history'),
            'description': 'Paramètres des APIs et services'
        }),
        ('Fichiers & Transitions', {
            'fields': ('max_upload_size_mb', 'default_comment_size', 'transition_animation_duration_ms'),
            'description': 'Configuration des uploads et animations'
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at', 'updated_by'),
            'classes': ('collapse',),
            'description': 'Informations de suivi'
        }),
    )

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        # Only allow one config instance
        return not Config.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Don't allow deletion of config
        return False


@admin.register(CuePoint)
class CuePointAdmin(admin.ModelAdmin):
    """Admin interface for CuePoint model"""

    list_display = ['track', 'slot', 'time', 'type', 'comment', 'created_at']
    list_filter = ['slot', 'type', 'created_at']
    search_fields = ['track__title', 'track__artist__name', 'time', 'type', 'comment']
    ordering = ['track__title', 'slot']

    fieldsets = (
        ('Cue Point Details', {
            'fields': ('track', 'slot', 'time', 'type', 'comment'),
            'description': 'Informations du point de repère'
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'Informations de suivi'
        }),
    )

    readonly_fields = ['created_at', 'updated_at']
