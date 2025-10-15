"""
Dynamic configuration service that replaces static constants with database values
"""
from ..models import Config


class ConfigService:
    """Service to access configuration values from database"""
    
    _config_cache = None
    
    @classmethod
    def get_config(cls):
        """Get configuration instance with caching"""
        if cls._config_cache is None:
            cls._config_cache = Config.get_config()
        return cls._config_cache
    
    @classmethod
    def refresh_cache(cls):
        """Refresh the cached configuration"""
        cls._config_cache = None
        return cls.get_config()
    
    # Refresh intervals
    @classmethod
    def get_refresh_interval_currently_playing_ms(cls):
        return cls.get_config().refresh_interval_currently_playing_ms
    
    @classmethod
    def get_refresh_interval_history_editing_ms(cls):
        return cls.get_config().refresh_interval_history_editing_ms
    
    # Icecast and playlist settings
    @classmethod
    def get_rubi_icecast_playlist_file(cls):
        return cls.get_config().rubi_icecast_playlist_file
    
    @classmethod
    def get_max_playlist_history_size(cls):
        return cls.get_config().max_playlist_history_size
    
    @classmethod
    def get_max_suggestions_auto_size(cls):
        return cls.get_config().max_suggestions_auto_size
    
    # Suggestions settings
    @classmethod
    def get_default_bpm_range_suggestions(cls):
        return cls.get_config().default_bpm_range_suggestions
    
    @classmethod
    def get_default_musical_key_distance(cls):
        return cls.get_config().default_musical_key_distance
    
    @classmethod
    def get_default_ranking_min(cls):
        return cls.get_config().default_ranking_min
    
    # UI Configuration
    @classmethod
    def get_max_title_length(cls):
        return cls.get_config().max_title_length
    
    @classmethod
    def get_max_artist_name_length(cls):
        return cls.get_config().max_artist_name_length
    
    # Database settings
    @classmethod
    def get_default_bpm(cls):
        return cls.get_config().default_bpm
    
    @classmethod
    def get_default_genre(cls):
        return cls.get_config().default_genre
    
    # API settings
    @classmethod
    def get_max_suggestions(cls):
        return cls.get_config().max_suggestions
    
    @classmethod
    def get_max_playlist_history(cls):
        return cls.get_config().max_playlist_history
    
    # File upload settings
    @classmethod
    def get_max_upload_size_mb(cls):
        return cls.get_config().max_upload_size_mb
    
    # Transition settings
    @classmethod
    def get_default_comment_size(cls):
        return cls.get_config().default_comment_size
    
    @classmethod
    def get_transition_animation_duration_ms(cls):
        return cls.get_config().transition_animation_duration_ms


# Backward compatibility - provide constants-like access
def get_config_value(attr_name):
    """Get a configuration value by attribute name"""
    config = ConfigService.get_config()
    return getattr(config, attr_name, None)


# Constants for backward compatibility
REFRESH_INTERVAL_CURRENTLY_PLAYING_MS = lambda: ConfigService.get_refresh_interval_currently_playing_ms()
REFRESH_INTERVAL_HISTORY_EDITING_MS = lambda: ConfigService.get_refresh_interval_history_editing_ms()
RUBI_ICECAST_PLAYLIST_FILE = lambda: ConfigService.get_rubi_icecast_playlist_file()
MAX_PLAYLIST_HISTORY_SIZE = lambda: ConfigService.get_max_playlist_history_size()
MAX_SUGGESTIONS_AUTO_SIZE = lambda: ConfigService.get_max_suggestions_auto_size()
MAX_TITLE_LENGTH = lambda: ConfigService.get_max_title_length()
MAX_ARTIST_NAME_LENGTH = lambda: ConfigService.get_max_artist_name_length()
DEFAULT_BPM = lambda: ConfigService.get_default_bpm()
DEFAULT_GENRE = lambda: ConfigService.get_default_genre()
MAX_SUGGESTIONS = lambda: ConfigService.get_max_suggestions()
MAX_PLAYLIST_HISTORY = lambda: ConfigService.get_max_playlist_history()
MAX_UPLOAD_SIZE_MB = lambda: ConfigService.get_max_upload_size_mb()
DEFAULT_COMMENT_SIZE = lambda: ConfigService.get_default_comment_size()
TRANSITION_ANIMATION_DURATION_MS = lambda: ConfigService.get_transition_animation_duration_ms()
