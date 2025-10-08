from django.contrib import admin

from django.db.models import F

from track.playlist.playlist_transitions import get_order_rank

# Register your models here.
from .models import Artist, Track, Genre, Playlist, TransitionType, Transition, CurrentlyPlaying, Collection, Config, CuePoint, TrackCuePoints


from django.forms import TextInput, Textarea
from django.db import models
from django import forms

from django.utils.safestring import mark_safe
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
    list_display = ['name', 'playlist_transitions']
    # list_display = ['name', 'id']
    search_fields = ['name']
    ordering = ['rank']

    def playlist_transitions(self, obj):
        return format_html("<a href='/track/playlist_transitions/{url}'>{label} (All Transitions)</a>", url=obj.id, label=obj.name)
    playlist_transitions.description='plop'

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
    
    list_display = ['__str__', 'time', 'type', 'comment', 'created_at']
    list_filter = ['type', 'created_at']
    search_fields = ['time', 'type', 'comment']
    ordering = ['time']
    
    fieldsets = (
        ('Cue Point Details', {
            'fields': ('time', 'type', 'comment'),
            'description': 'Informations du point de repère'
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'Informations de suivi'
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']


class CuePointInline(admin.TabularInline):
    """Inline for editing cue points in TrackCuePoints admin"""
    model = CuePoint
    extra = 0
    max_num = 8
    fields = ('time', 'type', 'comment')
    verbose_name = "Cue Point"
    verbose_name_plural = "Cue Points"


@admin.register(TrackCuePoints)
class TrackCuePointsAdmin(admin.ModelAdmin):
    """Admin interface for TrackCuePoints model"""
    
    list_display = ['track', 'get_cue_points_count', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['track__title', 'track__artist__name']
    ordering = ['track__title']
    
    fieldsets = (
        ('Track Information', {
            'fields': ('track',),
            'description': 'Piste associée'
        }),
        ('Cue Points', {
            'fields': (
                ('cue_point_1', 'cue_point_2'),
                ('cue_point_3', 'cue_point_4'),
                ('cue_point_5', 'cue_point_6'),
                ('cue_point_7', 'cue_point_8'),
            ),
            'description': '8 points de repère pour cette piste'
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'Informations de suivi'
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def get_cue_points_count(self, obj):
        """Count how many cue points are set for this track"""
        count = len(obj.get_cue_points_list())
        return f"{count}/8 cue points"
    
    get_cue_points_count.short_description = "Cue Points Count"
