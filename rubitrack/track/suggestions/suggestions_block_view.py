# Import mis à jour vers le nouveau module centralisé
from track.suggestions.core import get_suggestions_for_track


def suggestions_block(request, track_id):
    # return suggestions_list(request)
    return get_suggestions_for_track(track_id)
