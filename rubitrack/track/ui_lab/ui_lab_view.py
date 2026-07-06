"""
UI Lab — bac à sable de concepts UX/UI pour la page principale Now Playing.

Page autonome (ne modifie AUCUNE page existante). Affiche plusieurs concepts
d'interface pour "currently_playing", alimentés par de VRAIES données (track en
cours si dispo, sinon une track riche en cues + transitions), pour comparer.
"""

import re

from django.db.models import Count
from django.shortcuts import render

from ..models import Config, Track
from ..musical_key.musical_key_utils import get_musical_key_info
from ..currently_playing.currently_playing import (
    get_cue_points_slots_for_track,
    get_currently_playing_track,
    get_transitions_after,
)


def _camelot(key):
    if not key:
        return None
    info = get_musical_key_info(key)
    return info.get('camelot') if info else None


def _key_compat(key_a, key_b):
    """Compatibilité de mixage harmonique (roue Camelot)."""
    ca, cb = _camelot(key_a), _camelot(key_b)
    if not ca or not cb:
        return {'label': '?', 'color': '#adb5bd'}
    if ca == cb:
        return {'label': 'Parfait', 'color': '#2f9e44'}
    ma, mb = re.match(r'(\d+)([AB])', ca), re.match(r'(\d+)([AB])', cb)
    if not ma or not mb:
        return {'label': '?', 'color': '#adb5bd'}
    na, la = int(ma.group(1)), ma.group(2)
    nb, lb = int(mb.group(1)), mb.group(2)
    diff = (nb - na) % 12
    if na == nb and la != lb:
        return {'label': 'Relative', 'color': '#2f9e44'}
    if la == lb and diff in (1, 11):
        return {'label': 'Adjacent', 'color': '#37b24d'}
    if la == lb and diff == 2:
        return {'label': 'Énergie +', 'color': '#f08c00'}
    if la == lb and diff == 10:
        return {'label': 'Énergie -', 'color': '#f08c00'}
    return {'label': 'Risqué', 'color': '#e03131'}


def _duration(seconds):
    if not seconds:
        return None
    seconds = int(seconds)
    return f"{seconds // 60}:{seconds % 60:02d}"


def _pick_track():
    """Track en cours si dispo, sinon la plus riche (transitions sortantes + cues)."""
    track = get_currently_playing_track(with_refresh=False)
    if track:
        return track
    track = (
        Track.objects.annotate(
            n_out=Count('source', distinct=True), n_cues=Count('cue_points', distinct=True))
        .filter(n_out__gt=0, n_cues__gt=0)
        .select_related('artist', 'genre')
        .order_by('-n_out')
        .first()
    )
    if track:
        return track
    return Track.objects.select_related('artist').filter(source__isnull=False).first()


def _track_card(track):
    return {
        'obj': track,
        'title': track.title,
        'artist': track.artist.name if track.artist_id else '',
        'bpm': track.bpm,
        'key': track.musical_key or '',
        'camelot': _camelot(track.musical_key) or '',
        'color': track.get_musical_key_color(),
        'genre': track.genre.name if track.genre_id else '',
        'duration': _duration(track.playtime),
        'ranking': track.ranking or 0,
    }


def ui_lab_view(request):
    track = _pick_track()
    if not track:
        return render(request, 'track/ui_lab/ui_lab.html', {'no_data': True})

    separator = Config.get_config().separator_track_id
    after = (
        get_transitions_after(track)
        .exclude(track_destination_id=separator)
        .select_related('track_destination__artist')
        .order_by('-ranking', 'position')[:6]
    )
    candidates = []
    for transition in after:
        dest = transition.track_destination
        bpm_delta = None
        if dest.bpm and track.bpm:
            bpm_delta = round((dest.bpm - track.bpm) / track.bpm * 100, 1)
        card = _track_card(dest)
        card.update({
            'comment': transition.comment or '',
            'transition_ranking': transition.ranking,
            'bpm_delta': bpm_delta,
            'compat': _key_compat(track.musical_key, dest.musical_key),
        })
        candidates.append(card)

    return render(request, 'track/ui_lab/ui_lab.html', {
        'current': _track_card(track),
        'cue_slots': get_cue_points_slots_for_track(track),
        'candidates': candidates,
        'deck_b': candidates[0] if candidates else None,
    })
