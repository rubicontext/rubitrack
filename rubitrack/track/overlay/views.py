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


LAST_PLAYED_COUNT = 3


def _last_played(current_track):
    """Les 3 dernières tracks jouées avant la courante (séparateur exclu)."""
    from ..models import CurrentlyPlaying
    separator = Config.get_config().separator_track_id
    qs = (
        CurrentlyPlaying.objects.exclude(date_played__isnull=True)
        .exclude(track_id=separator)
        .select_related('track__artist')
        .order_by('-date_played')
    )
    plays = []
    for play in qs[:LAST_PLAYED_COUNT + 3]:   # marge pour sauter la courante
        if current_track and play.track_id == current_track.id and not plays:
            continue                           # saute l'entrée "en cours"
        track = play.track
        plays.append({
            'title': track.title,
            'artist': track.artist.name if track.artist_id else '',
            'key': track.musical_key or '',
            'color': track.get_musical_key_color(),
            'bpm': track.bpm,
            'time': play.date_played,
        })
        if len(plays) >= LAST_PLAYED_COUNT:
            break
    return plays


@login_required
def overlay2_view(request):
    """Variante avec blocs repliables: transitions + 3 dernières jouées."""
    context = _context()
    context['last_played'] = _last_played(context['track'])
    if request.GET.get('partial'):
        return render(request, 'track/overlay/_overlay2_content.html', context)
    return render(request, 'track/overlay/overlay2.html', context)
