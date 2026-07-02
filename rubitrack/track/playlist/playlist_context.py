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
        ordered_entries = list(
            playlist.playlist_tracks.select_related('track').order_by('position')
        )
        track_ids = [entry.track_id for entry in ordered_entries]

        try:
            current_position = track_ids.index(track_id)
        except ValueError:
            # Track courante pas trouvée dans cette playlist
            continue

        # Vérifier s'il y a une track suivante
        if current_position + 1 >= len(ordered_entries):
            continue
        next_track = ordered_entries[current_position + 1].track

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
            'playlist_name': playlist.name,
            'playlist_id': playlist.id,
            'transition_comment': transition_comment
        })

    return next_tracks_info
