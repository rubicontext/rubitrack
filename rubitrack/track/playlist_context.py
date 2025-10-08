import ast
from django.db import models
from track.models import Track, Transition
from track.playlist.playlist_transitions import get_playlists_by_track_id


def get_next_tracks_in_playlists(track_id):
    """
    Récupère toutes les tracks qui suivent immédiatement la track courante dans ses playlists
    
    Returns:
        List[dict]: Liste des tracks suivantes avec leurs infos de playlist et transition
        {
            'next_track': Track object,
            'playlist_name': str,
            'transition_comment': str or None
        }
    """
    current_track = Track.objects.get(id=track_id)
    playlists_with_track = get_playlists_by_track_id(track_id)
    
    next_tracks_info = []
    
    for playlist in playlists_with_track:
        playlist_name = playlist.name
        track_ids_str = playlist.track_ids
        
        # Vérifier que track_ids_str n'est pas None ou vide
        if not track_ids_str:
            continue
            
        # Parser la liste d'IDs avec ast.literal_eval
        try:
            track_ids = ast.literal_eval(track_ids_str)
        except (ValueError, SyntaxError):
            continue
        
        # Trouver la position de la track courante
        try:
            current_position = track_ids.index(track_id)
            
            # Vérifier s'il y a une track suivante
            if current_position + 1 < len(track_ids):
                next_track_id = track_ids[current_position + 1]
                
                try:
                    next_track = Track.objects.get(id=next_track_id)
                    
                    # Chercher une transition existante
                    transition_comment = None
                    try:
                        transition = Transition.objects.get(
                            track_source=current_track,
                            track_destination=next_track
                        )
                        transition_comment = transition.comment
                    except Transition.DoesNotExist:
                        pass
                    
                    next_tracks_info.append({
                        'next_track': next_track,
                        'playlist_name': playlist_name,
                        'playlist_id': playlist.id,
                        'transition_comment': transition_comment
                    })
                    
                except Track.DoesNotExist:
                    # Track suivante n'existe pas en base
                    continue
                    
        except ValueError:
            # Track courante pas trouvée dans cette playlist
            continue
    
    return next_tracks_info
