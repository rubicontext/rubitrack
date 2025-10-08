"""
Dynamic constants that read from database Config model
This replaces the static constants.py with dynamic values
"""
from track.models import Config


def get_config():
    """Get the current configuration from database"""
    return Config.get_config()


# Refresh intervals (in milliseconds)
def REFRESH_INTERVAL_CURRENTLY_PLAYING_MS():
    return get_config().refresh_interval_currently_playing_ms

def REFRESH_INTERVAL_HISTORY_EDITING_MS():
    return get_config().refresh_interval_history_editing_ms

# Icecast and playlist settings  
def RUBI_ICECAST_PLAYLIST_FILE():
    return get_config().rubi_icecast_playlist_file

def MAX_PLAYLIST_HISTORY_SIZE():
    return get_config().max_playlist_history_size

def MAX_SUGGESTIONS_AUTO_SIZE():
    return get_config().max_suggestions_auto_size

# UI Configuration
def MAX_TITLE_LENGTH():
    return get_config().max_title_length

def MAX_ARTIST_NAME_LENGTH():
    return get_config().max_artist_name_length

# Database settings
def DEFAULT_BPM():
    return get_config().default_bpm

def DEFAULT_GENRE():
    return get_config().default_genre

# API settings
def MAX_SUGGESTIONS():
    return get_config().max_suggestions

def MAX_PLAYLIST_HISTORY():
    return get_config().max_playlist_history

# File upload settings
def MAX_UPLOAD_SIZE_MB():
    return get_config().max_upload_size_mb

# Transition settings
def DEFAULT_COMMENT_SIZE():
    return get_config().default_comment_size

def TRANSITION_ANIMATION_DURATION_MS():
    return get_config().transition_animation_duration_ms


# Backward compatibility - static access for templates
class DynamicConfig:
    """Class to provide static-like access to dynamic config values"""
    
    @property
    def REFRESH_INTERVAL_CURRENTLY_PLAYING_MS(self):
        return REFRESH_INTERVAL_CURRENTLY_PLAYING_MS()
    
    @property 
    def REFRESH_INTERVAL_HISTORY_EDITING_MS(self):
        return REFRESH_INTERVAL_HISTORY_EDITING_MS()
    
    @property
    def RUBI_ICECAST_PLAYLIST_FILE(self):
        return RUBI_ICECAST_PLAYLIST_FILE()
    
    @property
    def MAX_PLAYLIST_HISTORY_SIZE(self):
        return MAX_PLAYLIST_HISTORY_SIZE()
    
    @property
    def MAX_SUGGESTIONS_AUTO_SIZE(self):
        return MAX_SUGGESTIONS_AUTO_SIZE()
    
    @property
    def MAX_TITLE_LENGTH(self):
        return MAX_TITLE_LENGTH()
    
    @property
    def MAX_ARTIST_NAME_LENGTH(self):
        return MAX_ARTIST_NAME_LENGTH()
    
    @property
    def DEFAULT_BPM(self):
        return DEFAULT_BPM()
    
    @property
    def DEFAULT_GENRE(self):
        return DEFAULT_GENRE()
    
    @property
    def MAX_SUGGESTIONS(self):
        return MAX_SUGGESTIONS()
    
    @property
    def MAX_PLAYLIST_HISTORY(self):
        return MAX_PLAYLIST_HISTORY()
    
    @property
    def MAX_UPLOAD_SIZE_MB(self):
        return MAX_UPLOAD_SIZE_MB()
    
    @property
    def DEFAULT_COMMENT_SIZE(self):
        return DEFAULT_COMMENT_SIZE()
    
    @property
    def TRANSITION_ANIMATION_DURATION_MS(self):
        return TRANSITION_ANIMATION_DURATION_MS()


# Global instance for easy access
config = DynamicConfig()
