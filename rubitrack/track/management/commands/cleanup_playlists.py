from django.core.management.base import BaseCommand
from track.models import Playlist, Track
import ast


class Command(BaseCommand):
    help = 'Clean up invalid track references in playlists'

    def handle(self, *args, **options):
        cleaned_playlists = 0
        cleaned_track_ids = 0
        
        # Clean up ManyToMany relationships
        for playlist in Playlist.objects.all():
            # Check ManyToMany tracks
            invalid_tracks = []
            for track in playlist.tracks.all():
                try:
                    # Try to access the track to see if it exists
                    track.title
                except Track.DoesNotExist:
                    invalid_tracks.append(track)
            
            if invalid_tracks:
                for invalid_track in invalid_tracks:
                    playlist.tracks.remove(invalid_track)
                    self.stdout.write(f"Removed invalid track {invalid_track.id} from playlist {playlist.name}")
                cleaned_playlists += 1
            
            # Clean up track_ids field
            if playlist.track_ids:
                try:
                    track_ids = ast.literal_eval(playlist.track_ids)
                    if isinstance(track_ids, list):
                        valid_track_ids = []
                        for track_id in track_ids:
                            if Track.objects.filter(id=track_id).exists():
                                valid_track_ids.append(track_id)
                            else:
                                self.stdout.write(f"Removed invalid track_id {track_id} from playlist {playlist.name}")
                                cleaned_track_ids += 1
                        
                        if len(valid_track_ids) != len(track_ids):
                            playlist.track_ids = str(valid_track_ids)
                            playlist.save()
                            
                except (ValueError, SyntaxError):
                    self.stdout.write(f"Warning: Invalid track_ids format in playlist {playlist.name}")
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Cleanup completed: {cleaned_playlists} playlists cleaned, {cleaned_track_ids} invalid track_ids removed'
            )
        )
