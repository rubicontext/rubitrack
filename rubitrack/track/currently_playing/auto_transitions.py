"""
Détection automatique de transitions depuis l'historique de lecture
(CurrentlyPlaying, alimenté par le log Icecast pendant les sets).

Deux morceaux joués consécutivement (gap <= MAX_GAP_MINUTES) forment un
enchaînement; s'il revient au moins MIN_OCCURRENCES fois et qu'aucune
transition n'existe encore, on la crée marquée "auto-détectée".
"""

import logging
from collections import Counter
from datetime import timedelta

from ..models import CurrentlyPlaying, Transition
from ..playlist.playlist_transitions import get_separator_track_id

logger = logging.getLogger(__name__)

AUTO_DETECTED_COMMENT_PREFIX = 'Auto-détectée depuis les sets'
MAX_GAP_MINUTES = 20
MIN_OCCURRENCES = 2


def detect_transitions_from_history() -> dict:
    """Analyse tout l'historique et crée les transitions récurrentes manquantes.

    Returns: {'pairs_seen', 'recurring', 'already_known', 'created'}
    """
    plays = list(
        CurrentlyPlaying.objects.exclude(date_played__isnull=True)
        .order_by('date_played')
        .values_list('track_id', 'date_played', named=True)
    )
    separator_id = get_separator_track_id()
    max_gap = timedelta(minutes=MAX_GAP_MINUTES)

    pair_counts: Counter = Counter()
    for prev, cur in zip(plays, plays[1:]):
        if prev.track_id == cur.track_id:
            continue
        if separator_id in (prev.track_id, cur.track_id):
            continue
        if cur.date_played - prev.date_played > max_gap:
            continue  # gap trop long: fin de set, pas un enchaînement
        pair_counts[(prev.track_id, cur.track_id)] += 1

    stats = {'pairs_seen': len(pair_counts), 'recurring': 0, 'already_known': 0, 'created': 0}
    existing = set(Transition.objects.values_list('track_source_id', 'track_destination_id'))

    for (source_id, destination_id), occurrences in pair_counts.items():
        if occurrences < MIN_OCCURRENCES:
            continue
        stats['recurring'] += 1
        if (source_id, destination_id) in existing:
            stats['already_known'] += 1
            continue
        Transition.objects.create(
            track_source_id=source_id,
            track_destination_id=destination_id,
            ranking=3,
            comment=f"{AUTO_DETECTED_COMMENT_PREFIX} (x{occurrences})",
        )
        stats['created'] += 1

    logger.info("Détection de transitions: %s", stats)
    return stats
