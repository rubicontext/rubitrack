"""
Reconstitution des sets depuis l'historique de lecture: deux morceaux
appartiennent au même set si l'écart entre eux est <= SET_GAP_MINUTES.
"""

from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from ..models import CurrentlyPlaying
from ..playlist.playlist_transitions import get_separator_track_id

SET_GAP_MINUTES = 30
MIN_TRACKS_PER_SET = 2


def build_sets(max_sets: int = 30) -> list:
    """Retourne les sets reconstitués, du plus récent au plus ancien.

    Chaque set: {'start', 'end', 'duration_minutes', 'plays': [CurrentlyPlaying],
                 'avg_bpm', 'tracklist_text'}
    """
    plays = list(
        CurrentlyPlaying.objects.exclude(date_played__isnull=True)
        .select_related('track__artist')
        .order_by('date_played')
    )
    separator_id = get_separator_track_id()
    plays = [p for p in plays if p.track_id != separator_id]

    gap = timedelta(minutes=SET_GAP_MINUTES)
    groups, current = [], []
    for play in plays:
        if current and play.date_played - current[-1].date_played > gap:
            groups.append(current)
            current = []
        current.append(play)
    if current:
        groups.append(current)

    sets = []
    for group in reversed(groups):
        if len(group) < MIN_TRACKS_PER_SET:
            continue
        bpms = [p.track.bpm for p in group if p.track.bpm]
        tracklist_lines = [
            f"{i:02d}. {p.track.artist.name} - {p.track.title}"
            for i, p in enumerate(group, start=1)
        ]
        sets.append({
            'start': group[0].date_played,
            'end': group[-1].date_played,
            'duration_minutes': int((group[-1].date_played - group[0].date_played).total_seconds() // 60),
            'plays': group,
            'avg_bpm': round(sum(bpms) / len(bpms), 1) if bpms else None,
            'tracklist_text': "\n".join(tracklist_lines),
        })
        if len(sets) >= max_sets:
            break
    return sets


@login_required
def display_sets(request):
    """Page 'Mes sets': historique des sessions + tracklist copiable."""
    return render(request, 'track/sets/sets.html', {'sets': build_sets()})
