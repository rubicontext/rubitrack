from typing import List

from django.db import models
from django.contrib.auth.models import User

Ranking_CHOICES = ((1, 'Poor'), (2, 'Average'), (3, 'Good'), (4, 'Very Good'), (5, 'Excellent'))


class Artist(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Genre(models.Model):
    name = models.CharField(max_length=3)
    description = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return self.name


class Track(models.Model):
    title = models.CharField(max_length=200)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    genre = models.ForeignKey(Genre, on_delete=models.CASCADE, blank=True, null=True)
    bpm = models.FloatField(blank=True, null=True)
    ranking = models.IntegerField(choices=Ranking_CHOICES, default=None, blank=True, null=True)
    musical_key = models.CharField(max_length=3, blank=True, null=True)
    file_name = models.CharField(max_length=200, blank=True, null=True)
    comment = models.CharField(max_length=500, blank=True, null=True)
    comment2 = models.CharField(max_length=500, blank=True, null=True)
    position = models.PositiveIntegerField(default=0, blank=False, null=False, db_index=True)
    bitrate = models.IntegerField(blank=True, null=True)
    playcount = models.IntegerField(blank=True, null=True)
    energy = models.IntegerField(blank=True, null=True)
    playtime = models.FloatField(blank=True, null=True, help_text="Durée en secondes (PLAYTIME Traktor)")
    audio_id = models.CharField(max_length=2000, blank=True, null=True, db_index=True)
    location_dir = models.CharField(max_length=2000, blank=True, null=True)
    file_path = models.CharField(max_length=2000, blank=True, null=True, db_index=True)

    # all dates
    date_collection_created = models.DateTimeField('date added to collection', auto_now_add=True, blank=True, null=True)
    date_collection_updated = models.DateTimeField(
        'date of modification in collection', auto_now_add=True, blank=True, null=True
    )
    date_collection_source_updated = models.DateTimeField(
        'date of modification in the source collection (Traktor/Serato/Rekordbox)',
        auto_now_add=True,
        blank=True,
        null=True,
    )
    date_last_played = models.DateTimeField('date last played', blank=True, null=True)

    def __repr__(self):
        return f'Track({self.title}, {self.artist.name}, {self.genre.name if self.genre else "N/A"}, {self.bpm if self.bpm else "N/A"}, {self.musical_key if self.musical_key else "N/A"}, {self.ranking if self.ranking else "N/A"})'

    class Meta(object):
        ordering = ['position']

    def __str__(self):
        return self.title + " - " + self.artist.name

    def get_track_cue_points_text(self):
        """
        Retourne une chaîne de texte compact avec les cue points de la track
        Format: "1=0:30, 2=1:15, 3=2:45" etc.
        """
        return ", ".join(f"{cp.slot}={cp.time}" for cp in self.cue_points.all())

    def get_cue_points_by_slot(self):
        """Retourne un dict {slot: CuePoint} pour les slots occupés (1..8)."""
        return {cp.slot: cp for cp in self.cue_points.all()}

    def get_musical_key_color(self):
        """
        Retourne la couleur hexadécimale Traktor associée à la clé musicale du track
        """
        if not self.musical_key:
            return '#cccccc'

        # Import local pour éviter la circularité
        from .templatetags.musical_key_filters import get_musical_key_info

        key_info = get_musical_key_info(self.musical_key)
        if not key_info:
            return '#cccccc'
        return key_info.get('color_hex', '#cccccc')

    def get_musical_key_obj(self):
        """
        Retourne l'objet MusicalKey correspondant à la clé musicale du track
        """
        from .musical_key.musical_key_models import MusicalKey
        if not self.musical_key:
            return None
        try:
            return MusicalKey.objects.get(musical=self.musical_key)
        except MusicalKey.DoesNotExist:
            return None

    def get_last_four_cue_points_text_no_ms(self) -> str:
        """Return a compact string of times for cue points 5..8 without milliseconds.
        Missing cue points are rendered as '_' segments. Example: "3:31|_|3:45|4:01" when slot 6 missing.
        """
        by_slot = self.get_cue_points_by_slot()
        parts: List[str] = []
        for i in range(5, 9):
            cp = by_slot.get(i)
            parts.append((cp.get_time_without_ms() or '_') if cp else '_')
        return "|".join(parts)

    def get_all_cue_points_text_no_ms(self) -> str:
        """Return 8 cue points (slots 1..8) times without milliseconds.
        First 4 joined by '|', then '//', then last 4 joined by '|'. Missing -> '_'.
        """
        by_slot = self.get_cue_points_by_slot()
        segments = [
            (by_slot[i].get_time_without_ms() or '_') if i in by_slot else '_'
            for i in range(1, 9)
        ]
        return "|".join(segments[:4]) + "//" + "|".join(segments[4:])


class Playlist(models.Model):
    name = models.CharField(max_length=200)
    tracks = models.ManyToManyField(Track, through='PlaylistTrack')
    rank = models.IntegerField(blank=True, null=True)
    collection = models.ForeignKey('Collection', on_delete=models.CASCADE)

    def __str__(self):
        return self.name

    def get_ordered_track_ids(self):
        """IDs des tracks dans l'ordre de la playlist."""
        return list(
            self.playlist_tracks.order_by('position').values_list('track_id', flat=True)
        )

    def get_ordered_tracks(self):
        """Tracks dans l'ordre de la playlist (une seule requête)."""
        return [
            pt.track
            for pt in self.playlist_tracks.select_related('track').order_by('position')
        ]

    def set_tracks(self, tracks):
        """Remplace le contenu de la playlist par `tracks`, dans cet ordre.
        Les doublons sont dédupliqués (première occurrence conservée)."""
        self.playlist_tracks.all().delete()
        entries = []
        seen = set()
        for track in tracks:
            if track.pk in seen:
                continue
            seen.add(track.pk)
            entries.append(PlaylistTrack(playlist=self, track=track, position=len(entries)))
        PlaylistTrack.objects.bulk_create(entries)


class PlaylistTrack(models.Model):
    """Liaison playlist/track ordonnée (remplace l'ancien champ texte track_ids)."""
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name='playlist_tracks')
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name='playlist_entries')
    position = models.PositiveIntegerField()

    class Meta:
        ordering = ['position']
        constraints = [
            models.UniqueConstraint(fields=['playlist', 'track'], name='unique_playlist_track'),
        ]
        indexes = [
            models.Index(fields=['playlist', 'position'], name='track_playl_playlis_pos_idx'),
        ]

    def __str__(self):
        return f"{self.playlist.name}[{self.position}] {self.track.title}"


class Collection(models.Model):
    name = models.CharField(max_length=200, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    tracks = models.ManyToManyField(Track)

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = self.user.username
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class TransitionType(models.Model):
    name = models.CharField(max_length=50)
    acronym = models.CharField(max_length=3, blank=True, null=True)
    description = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return self.name


class Transition(models.Model):
    track_source = models.ForeignKey(Track, related_name="source", on_delete=models.CASCADE)
    track_destination = models.ForeignKey(Track, related_name="destination", on_delete=models.CASCADE)
    transition_type = models.ForeignKey(TransitionType, on_delete=models.CASCADE, null=True)
    ranking = models.IntegerField(choices=Ranking_CHOICES, default=3)
    comment = models.TextField(max_length=200, blank=True, null=True)
    # used for sortable admin
    position = models.PositiveIntegerField(default=0, blank=False, null=False)

    class Meta(object):
        ordering = ['position']

    def __str__(self):
        return self.track_source.title + " - " + self.track_destination.title


class CurrentlyPlaying(models.Model):
    date_played = models.DateTimeField('date played', blank=True, null=True)
    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    related_to_current_track = False
    related_to_current_track_text = ''

    def __str__(self):
        return self.track.title + " - " + self.date_played.strftime("%H:%M:%S, %d/%m/%Y")


class Config(models.Model):
    """
    Configuration model to store application settings in database
    This replaces the static constants.py values with dynamic database values
    """

    # Refresh intervals (in milliseconds)
    refresh_interval_currently_playing_ms = models.IntegerField(default=10000, help_text="Refresh interval for currently playing page (milliseconds)")
    refresh_interval_history_editing_ms = models.IntegerField(default=30000, help_text="Refresh interval for history editing page (milliseconds)")

    # Icecast and playlist settings
    rubi_icecast_playlist_file = models.CharField(max_length=500, default='/var/log/icecast2/playlist.log', help_text="Path to Icecast playlist log file")
    max_playlist_history_size = models.IntegerField(default=10, help_text="Maximum number of tracks in playlist history")
    max_suggestions_auto_size = models.IntegerField(default=20, help_text="Maximum number of automatic suggestions")

    # Suggestions settings (History Editing defaults)
    default_bpm_range_suggestions = models.IntegerField(default=3, help_text="Default BPM range for suggestions slider (%)")
    default_musical_key_distance = models.IntegerField(default=3, help_text="Default musical key distance for suggestions slider")
    default_ranking_min = models.IntegerField(default=3, help_text="Default minimum ranking for suggestions slider")

    # Currently Playing specific suggestion params
    currently_bpm_range_suggestions = models.IntegerField(default=3, help_text="BPM range (%) for currently playing suggestions")
    currently_musical_key_distance = models.IntegerField(default=4, help_text="Musical key max distance for currently playing suggestions")
    currently_ranking_min = models.IntegerField(default=1, help_text="Minimum ranking for currently playing suggestions")

    # UI Configuration
    max_title_length = models.IntegerField(default=20, help_text="Maximum title length for display")
    max_artist_name_length = models.IntegerField(default=20, help_text="Maximum artist name length for display")

    # Database settings
    default_bpm = models.FloatField(default=120.0, help_text="Default BPM value for new tracks")
    default_genre = models.CharField(max_length=50, default="Unknown", help_text="Default genre for new tracks")

    # API settings
    max_suggestions = models.IntegerField(default=10, help_text="Maximum number of suggestions returned by API")
    max_playlist_history = models.IntegerField(default=50, help_text="Maximum number of tracks in playlist history")

    # File upload settings
    max_upload_size_mb = models.IntegerField(default=10, help_text="Maximum file upload size in MB")

    # Transition settings
    default_comment_size = models.IntegerField(default=60, help_text="Default size for transition comments")
    transition_animation_duration_ms = models.IntegerField(
        default=300, help_text="Duration of transition animations (milliseconds)"
    )

    # Playlist settings
    default_playlist_favourites = models.CharField(
        max_length=500,
        default="634;611;621;616;630",
        help_text="Default favourite playlist IDs (semicolon-separated)"
    )
    separator_track_id = models.IntegerField(
        default=14294,
        help_text="ID of the separator track used to split playlists (instance-specific)"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Configuration"
        verbose_name_plural = "Configurations"

    def __str__(self):
        return f"Config updated on {self.updated_at.strftime('%Y-%m-%d %H:%M:%S')}"

    # Cache process-level: la config est lue partout, une requête par appel est inutile.
    # Invalidé à chaque save() ; app mono-utilisateur, la staleness inter-process est acceptable.
    _config_cache = None

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        type(self)._config_cache = None

    @classmethod
    def get_config(cls):
        """Get the current configuration (cached), create one if it doesn't exist"""
        if cls._config_cache is None:
            cls._config_cache, _ = cls.objects.get_or_create(pk=1)
        return cls._config_cache

    @classmethod
    def clear_cache(cls):
        cls._config_cache = None


class CuePoint(models.Model):
    """
    Cue point d'une track, rattaché à un slot 1..8 (RCueN / Traktor HOTCUE N-1)
    """
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name='cue_points')
    slot = models.PositiveSmallIntegerField(help_text="Slot 1-8 (RCueN, Traktor HOTCUE = slot - 1)")

    time = models.CharField(max_length=20, null=True, blank=True)
    # Precise Traktor milliseconds with up to 6 fractional digits
    time_ms = models.DecimalField(max_digits=16, decimal_places=6, null=True, blank=True)
    len_ms = models.DecimalField(max_digits=16, decimal_places=6, null=True, blank=True)
    type = models.CharField(max_length=50, blank=True, null=True, help_text="Type of cue point")
    comment = models.TextField(max_length=200, blank=True, null=True, help_text="Comment for this cue point")

    # Nouveaux champs pour supporter les loops et types Traktor
    end_time = models.CharField(max_length=20, null=True, blank=True)
    duration = models.FloatField(null=True, blank=True)
    traktor_type = models.CharField(max_length=10, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cue Point"
        verbose_name_plural = "Cue Points"
        ordering = ['slot']
        constraints = [
            models.UniqueConstraint(fields=['track', 'slot'], name='unique_cuepoint_track_slot'),
        ]

    def __str__(self) -> str:
        return f"CuePoint(slot={self.slot}, {self.time})"

    def get_time_without_ms(self) -> str:
        """
        Return a human-readable time without milliseconds.
        Priority:
        - If `time` is present (e.g., "1:23.456" or "1:23"), strip any fractional part.
        - Else if `time_ms` is present, format as "M:SS".
        - Else return empty string.
        """
        if self.time:
            return str(self.time).split('.')[0]
        if self.time_ms is not None:
            try:
                total_ms = float(self.time_ms)
                total_seconds = int(round(total_ms / 1000.0))
                minutes = total_seconds // 60
                seconds = total_seconds % 60
                return f"{minutes}:{seconds:02d}"
            except (ValueError, TypeError):
                return ""
        return ""


