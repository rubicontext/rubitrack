from ..rubi_conf import MAX_SUGGESTIONS_AUTO_SIZE
from track.models import Track


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

    listTracks = (
        Track.objects.filter(
            comment__icontains=track.genre,
            musical_key=track.musical_key,
            bpm__gte=track.bpm - 5,
            bpm__lte=track.bpm + 5,
        )
        .exclude(id=track.id)
        .order_by('bpm')
    )

    if len(listTracks) > MAX_SUGGESTIONS_AUTO_SIZE:
        listTracks = listTracks[0: MAX_SUGGESTIONS_AUTO_SIZE - 1]
    return listTracks


