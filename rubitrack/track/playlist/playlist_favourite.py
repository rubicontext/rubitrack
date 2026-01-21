from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from typing import List
from django.http import HttpRequest, HttpResponse

from ..models import Playlist
from .playlist_transitions import get_transitions_from_playlist, get_ordered_tracks_from_playlist

# Default favourite playlist IDs (semicolon-separated). Update to your own defaults.
DEFAULT_PLAYLIST_FAVOURITES = "634;611;621;616;621"


@login_required
def playlist_favourite(request: HttpRequest) -> HttpResponse:
    """Display transitions for multiple playlists selected by semicolon-separated IDs.
    Query param or POST field: ids="1;2;3"
    """
    ids_raw = (request.GET.get('ids') or request.POST.get('ids') or DEFAULT_PLAYLIST_FAVOURITES)
    playlist_ids: List[int] = []
    for part in ids_raw.split(';'):
        part = part.strip()
        if not part:
            continue
        try:
            playlist_ids.append(int(part))
        except ValueError:
            continue

    playlists = []
    for pid in playlist_ids:
        try:
            pl = Playlist.objects.get(id=pid)
        except Playlist.DoesNotExist:
            continue
        transitions = get_transitions_from_playlist(pl)
        ordered_tracks = get_ordered_tracks_from_playlist(pl)
        first_track = ordered_tracks[0] if ordered_tracks else None
        playlists.append({
            'playlist': pl,
            'transitions': transitions,
            'firstTrack': first_track,
        })

    return render(request, 'track/playlists/playlist_favourite.html', {
        'ids': ids_raw,
        'playlists': playlists,
    })
