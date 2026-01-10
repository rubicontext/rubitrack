import datetime

from django.db import models
from django.utils import timezone
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
    position = models.PositiveIntegerField(default=0, blank=False, null=False)
    bitrate = models.IntegerField(blank=True, null=True)
    playcount = models.IntegerField(blank=True, null=True)
    energy = models.IntegerField(blank=True, null=True)
    audio_id = models.CharField(max_length=2000, blank=True, null=True)
    location_dir = models.CharField(max_length=2000, blank=True, null=True)
    file_path = models.CharField(max_length=2000, blank=True, null=True)

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
        try:
            track_cue_points = self.cue_points
            cue_points_list = track_cue_points.get_cue_points_list()
            
            if not cue_points_list:
                return ""
            
            # Créer la liste des couples numéro=temps
            cue_text_parts = []
            for i in range(1, 9):
                cue_point = getattr(track_cue_points, f'cue_point_{i}')
                if cue_point:
                    cue_text_parts.append(f"{i}={cue_point.time}")
            
            return ", ".join(cue_text_parts)
            
        except TrackCuePoints.DoesNotExist:
            return ""

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
        Missing cue points are rendered as '_' segments. Example: "3:31/_/3:45/4:01" when slot 6 missing.
        """
        try:
            if not hasattr(self, 'cue_points') or not self.cue_points:
                return "_|_|_|_"  # 4 segments empty
            parts: List[str] = []
            for i in range(5, 9):
                cp = getattr(self.cue_points, f'cue_point_{i}', None)
                if cp:
                    val = cp.get_time_without_ms() if hasattr(cp, 'get_time_without_ms') else (cp.time or '')
                    parts.append(val if val else '_')
                else:
                    parts.append('_')
            return "|".join(parts)
        except Exception:
            return "_|_|_|_"

    def get_all_cue_points_text_no_ms(self) -> str:
        """Return 8 cue points (slots 1..8) times without milliseconds.
        First 4 joined by '/', then '//', then last 4 joined by '/'. Missing -> '_'.
        """
        try:
            if not hasattr(self, 'cue_points') or not self.cue_points:
                return "|".join(["_"] * 4) + "//" + "|".join(["_"] * 4)
            parts_first: List[str] = []
            parts_last: List[str] = []
            for i in range(1, 9):
                cp = getattr(self.cue_points, f'cue_point_{i}', None)
                if cp:
                    val = cp.get_time_without_ms() if hasattr(cp, 'get_time_without_ms') else (cp.time or '')
                    segment = val if val else '_'
                else:
                    segment = '_'
                if i <= 4:
                    parts_first.append(segment)
                else:
                    parts_last.append(segment)
            return "|".join(parts_first) + "//" + "|".join(parts_last)
        except Exception:
            return "|".join(["_"] * 4) + "//" + "|".join(["_"] * 4)


class Playlist(models.Model):
    name = models.CharField(max_length=200)
    track_ids = models.CharField(max_length=20000, blank=True, null=True)
    tracks = models.ManyToManyField(Track)
    rank = models.IntegerField(blank=True, null=True)
    collection = models.ForeignKey('Collection', on_delete=models.CASCADE)

    def __str__(self):
        return self.name


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
    transition_animation_duration_ms = models.IntegerField(default=300, help_text="Duration of transition animations (milliseconds)")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = "Configuration"
        verbose_name_plural = "Configurations"
    
    def __str__(self):
        return f"Config updated on {self.updated_at.strftime('%Y-%m-%d %H:%M:%S')}"
    
    @classmethod
    def get_config(cls):
        """Get the current configuration, create one if it doesn't exist"""
        config, _ = cls.objects.get_or_create(pk=1)
        return config


class CuePoint(models.Model):
    """
    Model to store individual cue points with their position, type and comment
    """
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
        ordering = ['time']
    
    def __str__(self) -> str:
        return f"CuePoint({self.time})"

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
            except Exception:
                return ""
        return ""


class TrackCuePoints(models.Model):
    """
    Model to store 8 cue points for each track
    Uses track.id as primary key
    """
    track = models.OneToOneField(Track, on_delete=models.CASCADE, primary_key=True, related_name='cue_points')
    
    # 8 cue points for each track
    cue_point_1 = models.ForeignKey(CuePoint, on_delete=models.SET_NULL, null=True, blank=True, related_name='track_cue_1')
    cue_point_2 = models.ForeignKey(CuePoint, on_delete=models.SET_NULL, null=True, blank=True, related_name='track_cue_2')
    cue_point_3 = models.ForeignKey(CuePoint, on_delete=models.SET_NULL, null=True, blank=True, related_name='track_cue_3')
    cue_point_4 = models.ForeignKey(CuePoint, on_delete=models.SET_NULL, null=True, blank=True, related_name='track_cue_4')
    cue_point_5 = models.ForeignKey(CuePoint, on_delete=models.SET_NULL, null=True, blank=True, related_name='track_cue_5')
    cue_point_6 = models.ForeignKey(CuePoint, on_delete=models.SET_NULL, null=True, blank=True, related_name='track_cue_6')
    cue_point_7 = models.ForeignKey(CuePoint, on_delete=models.SET_NULL, null=True, blank=True, related_name='track_cue_7')
    cue_point_8 = models.ForeignKey(CuePoint, on_delete=models.SET_NULL, null=True, blank=True, related_name='track_cue_8')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Track Cue Points"
        verbose_name_plural = "Track Cue Points"
    
    def __str__(self) -> str:
        return f"Cue Points for {self.track.title}"
    
    def get_cue_points_list(self):
        """Return a list of all non-null cue points"""
        cue_points = []
        for i in range(1, 9):
            cue_point = getattr(self, f'cue_point_{i}')
            if cue_point:
                cue_points.append(cue_point)
        return cue_points
    
    def get_cue_points(self):
        """Return an array of 8 cue points (including None for empty slots)"""
        cue_points = []
        for i in range(1, 9):
            cue_point = getattr(self, f'cue_point_{i}')
            cue_points.append(cue_point)
        return cue_points
    
    def get_cue_point_by_number(self, number):
        """Get a specific cue point by number (1-8)"""
        if 1 <= number <= 8:
            return getattr(self, f'cue_point_{number}')
        return None
    
    def set_cue_point_by_number(self, number, cue_point):
        """Set a specific cue point by number (1-8)"""
        if 1 <= number <= 8:
            setattr(self, f'cue_point_{number}', cue_point)
            return True
        return False
    
    def get_cue_points_for_export(self):
        """
        Retourne les cue points sous forme de liste de tuples pour l'export
        Format: [(num, time_seconds), ...]
        """
        cue_points_export = []
        for i in range(1, 9):
            cue_point = getattr(self, f'cue_point_{i}')
            if cue_point:
                cue_points_export.append((i, cue_point.time))
        return cue_points_export

    def get_cue_points_for_display_no_ms(self) -> List[Tuple[int, str]]:
        """
        Retourne les cue points sous forme de liste de tuples pour l'affichage sans millisecondes
        Format: [(num, time_no_ms), ...]
        """
        result: List[Tuple[int, str]] = []
        for i in range(1, 9):
            cue_point = getattr(self, f'cue_point_{i}')
            if cue_point:
                result.append((i, cue_point.get_time_without_ms()))
        return result
