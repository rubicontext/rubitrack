"""
Set Builder — page autonome (ne touche à aucune page existante).

Exploite le fait que la table Transition EST un graphe orienté
(track_source -> track_destination). Deux usages combinés :
  - visualisation graphe du réseau de transitions,
  - lookahead +1/+2/+3… : depuis une track de départ, on déroule les
    prochaines transitions en profondeur (extension du "+1" de Now Playing).
"""

import logging

from django.http import JsonResponse
from django.shortcuts import render

from ..models import Config, Track, Transition

logger = logging.getLogger(__name__)

MAX_DEPTH = 6
DEFAULT_DEPTH = 3
MAX_BRANCH = 8
DEFAULT_BRANCH = 4


def _separator_id():
    return Config.get_config().separator_track_id


def set_builder_view(request):
    """Page: choix d'une track de départ + profondeur, rendu du graphe côté client."""
    tracks = Track.objects.select_related('artist').order_by('artist__name', 'title')
    start_id = request.GET.get('track_id')
    return render(request, 'track/set_builder/set_builder.html', {
        'tracks': tracks,
        'start_id': int(start_id) if start_id and start_id.isdigit() else None,
        'default_depth': DEFAULT_DEPTH,
        'default_branch': DEFAULT_BRANCH,
        'max_depth': MAX_DEPTH,
        'max_branch': MAX_BRANCH,
    })


def _node_dict(track, depth):
    return {
        'id': track.id,
        'title': track.title or '(sans titre)',
        'artist': track.artist.name if track.artist_id else '',
        'bpm': float(track.bpm) if track.bpm is not None else None,
        'key': track.musical_key or '',
        'color': track.get_musical_key_color(),
        'ranking': track.ranking or 0,
        'depth': depth,
    }


def set_builder_graph_api(request, track_id):
    """JSON: graphe forward par BFS (track_source -> track_destination) jusqu'à `depth`.
    Branchement borné à `branch` meilleures transitions (ranking) par track."""
    try:
        depth = min(max(int(request.GET.get('depth', DEFAULT_DEPTH)), 1), MAX_DEPTH)
        branch = min(max(int(request.GET.get('branch', DEFAULT_BRANCH)), 1), MAX_BRANCH)
    except (TypeError, ValueError):
        depth, branch = DEFAULT_DEPTH, DEFAULT_BRANCH

    try:
        start = Track.objects.select_related('artist').get(id=track_id)
    except Track.DoesNotExist:
        return JsonResponse({'error': 'track introuvable'}, status=404)

    separator = _separator_id()
    nodes = {start.id: _node_dict(start, 0)}
    edges = []
    truncated = 0
    frontier = [start.id]

    for current_depth in range(1, depth + 1):
        next_frontier = []
        for source_id in frontier:
            qs = (
                Transition.objects.filter(track_source_id=source_id)
                .exclude(track_destination_id=separator)
                .select_related('track_destination__artist', 'transition_type')
                .order_by('-ranking', 'position')
            )
            total = qs.count()
            picked = list(qs[:branch])
            if total > branch:
                truncated += total - branch
            for transition in picked:
                destination = transition.track_destination
                edges.append({
                    'source': source_id,
                    'target': destination.id,
                    'ranking': transition.ranking,
                    'comment': transition.comment or '',
                    'type': transition.transition_type.name if transition.transition_type_id else '',
                })
                if destination.id not in nodes:
                    nodes[destination.id] = _node_dict(destination, current_depth)
                    next_frontier.append(destination.id)
        frontier = next_frontier
        if not frontier:
            break

    return JsonResponse({
        'start_id': start.id,
        'nodes': list(nodes.values()),
        'edges': edges,
        'truncated': truncated,
        'depth': depth,
        'branch': branch,
    })
