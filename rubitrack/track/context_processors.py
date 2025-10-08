"""
Context processor to make configuration values available in all templates
"""
from track.models import Config


def config_context(request):
    """
    Context processor to add configuration values to all template contexts
    """
    try:
        config = Config.get_config()
        return {
            'CONFIG': {
                'REFRESH_INTERVAL_CURRENTLY_PLAYING_MS': config.refresh_interval_currently_playing_ms,
                'REFRESH_INTERVAL_HISTORY_EDITING_MS': config.refresh_interval_history_editing_ms,
                'RUBI_ICECAST_PLAYLIST_FILE': config.rubi_icecast_playlist_file,
                'MAX_PLAYLIST_HISTORY_SIZE': config.max_playlist_history_size,
                'MAX_SUGGESTIONS_AUTO_SIZE': config.max_suggestions_auto_size,
                'DEFAULT_BPM_RANGE_SUGGESTIONS': config.default_bpm_range_suggestions,
                'DEFAULT_MUSICAL_KEY_DISTANCE': config.default_musical_key_distance,
                'DEFAULT_RANKING_MIN': config.default_ranking_min,
                'MAX_TITLE_LENGTH': config.max_title_length,
                'MAX_ARTIST_NAME_LENGTH': config.max_artist_name_length,
                'DEFAULT_BPM': config.default_bpm,
                'DEFAULT_GENRE': config.default_genre,
                'MAX_SUGGESTIONS': config.max_suggestions,
                'MAX_PLAYLIST_HISTORY': config.max_playlist_history,
                'MAX_UPLOAD_SIZE_MB': config.max_upload_size_mb,
                'DEFAULT_COMMENT_SIZE': config.default_comment_size,
                'TRANSITION_ANIMATION_DURATION_MS': config.transition_animation_duration_ms,
            }
        }
    except Exception:
        # Fallback to static values if config is not available
        return {
            'CONFIG': {
                'REFRESH_INTERVAL_CURRENTLY_PLAYING_MS': 10000,
                'REFRESH_INTERVAL_HISTORY_EDITING_MS': 30000,
                'RUBI_ICECAST_PLAYLIST_FILE': '/var/log/icecast2/playlist.log',
                'MAX_PLAYLIST_HISTORY_SIZE': 10,
                'MAX_SUGGESTIONS_AUTO_SIZE': 20,
                'DEFAULT_BPM_RANGE_SUGGESTIONS': 3,
                'DEFAULT_MUSICAL_KEY_DISTANCE': 3,
                'DEFAULT_RANKING_MIN': 3,
                'MAX_TITLE_LENGTH': 20,
                'MAX_ARTIST_NAME_LENGTH': 20,
                'DEFAULT_BPM': 120.0,
                'DEFAULT_GENRE': 'Unknown',
                'MAX_SUGGESTIONS': 10,
                'MAX_PLAYLIST_HISTORY': 50,
                'MAX_UPLOAD_SIZE_MB': 10,
                'DEFAULT_COMMENT_SIZE': 60,
                'TRANSITION_ANIMATION_DURATION_MS': 300,
            }
        }
