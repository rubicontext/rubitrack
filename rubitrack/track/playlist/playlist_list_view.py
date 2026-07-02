from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Q
from ..models import Playlist, Config
from .playlist_transitions import get_order_rank


@login_required
def playlist_list_view(request):
    """
    Display a standalone list of all playlists with favourite star functionality
    Independent from Django admin to avoid menu/layout issues
    """
    # Get search query if any
    search_query = request.GET.get('q', '').strip()

    # Get all playlists
    if search_query:
        playlists = Playlist.objects.filter(
            Q(name__icontains=search_query)
        ).select_related('collection')
    else:
        playlists = Playlist.objects.all().select_related('collection')

    # Order playlists using the same logic as admin
    playlists_list = list(playlists)
    playlists_sorted = sorted(
        playlists_list,
        key=lambda p: (get_order_rank(p.name), -p.id)  # ID décroissant si même rank
    )

    # Get favourite playlist IDs from config
    config = Config.get_config()
    favourite_ids = [x.strip() for x in config.default_playlist_favourites.split(';') if x.strip()]

    # Add is_favourite flag to each playlist
    for playlist in playlists_sorted:
        playlist.is_favourite = str(playlist.id) in favourite_ids

    context = {
        'playlists': playlists_sorted,
        'search_query': search_query,
        'total_count': len(playlists_sorted),
        'favourite_ids': favourite_ids,
    }

    return render(request, 'track/playlists/playlist_list.html', context)
