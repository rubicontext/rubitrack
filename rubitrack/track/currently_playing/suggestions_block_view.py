# Import temporaire
from track.suggestions.suggestions_view import get_suggestions_for_track, ajax_suggestions

def suggestions_block(request, track_id):
    from track.suggestions_view import suggestions_list
    return suggestions_list(request)
