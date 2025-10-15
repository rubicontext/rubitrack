from track.models import Track, Config


def get_suggestions_same_artist(track):
    suggestions = None
    if track is not None:
        suggestions = Track.objects.filter(artist=track.artist)
    return suggestions


def get_list_track_suggestions_auto(track):
    """we get tracks :
    - same key
    - same genre or sub genre
    - same BPM +/- 5
    - not the same track"""

    # if no BPM, track is corrucpted/created on the fly with no suggestion available
    if track is None or track.bpm is None:
        return None

    list_tracks = (
        Track.objects.filter(
            comment__icontains=track.genre,
            musical_key=track.musical_key,
            bpm__gte=track.bpm - 5,
            bpm__lte=track.bpm + 5,
        )
        .exclude(id=track.id)
        .order_by('bpm')
    )

    # Get max suggestions from config
    config = Config.get_config()
    max_suggestions = config.max_suggestions_auto_size
    
    if len(list_tracks) > max_suggestions:
        list_tracks = list_tracks[0: max_suggestions - 1]
    return list_tracks


