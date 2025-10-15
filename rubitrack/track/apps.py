from django.apps import AppConfig


class TrackConfig(AppConfig):
    name = 'track'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        # Import template tags modules to ensure registration
        try:
            import track.musical_key.musical_key_filters  # noqa: F401
        except Exception:
            pass
