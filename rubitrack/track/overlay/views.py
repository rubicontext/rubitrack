"""
Overlay — mini-vue compacte à poser par-dessus Traktor (petite fenêtre
navigateur + PowerToys Always On Top).

Page autonome (/track/overlay/), ne touche à aucune page existante.
Affiche: track en cours + prochaines transitions triées par play_count
(enchaînements réellement joués), rafraîchi toutes les 10 s sans flicker.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from ..models import Config
from ..currently_playing.currently_playing import (
    get_currently_playing_track,
    get_transitions_after,
)

MAX_NEXT = 4


def _context():
    track = get_currently_playing_track(with_refresh=True)
    nexts = []
    if track:
        separator = Config.get_config().separator_track_id
        transitions = (
            get_transitions_after(track)
            .exclude(track_destination_id=separator)
            .select_related('track_destination__artist')
            .order_by('-play_count', '-ranking', 'position')[:MAX_NEXT]
        )
        for transition in transitions:
            dest = transition.track_destination
            nexts.append({
                'title': dest.title,
                'artist': dest.artist.name if dest.artist_id else '',
                'key': dest.musical_key or '',
                'color': dest.get_musical_key_color(),
                'bpm': dest.bpm,
                'play_count': transition.play_count,
                'ranking': transition.ranking,
                'comment': transition.comment or '',
            })
    return {'track': track, 'nexts': nexts}


@login_required
def overlay_view(request):
    context = _context()
    if request.GET.get('partial'):
        return render(request, 'track/overlay/_overlay_content.html', context)
    return render(request, 'track/overlay/overlay.html', context)
