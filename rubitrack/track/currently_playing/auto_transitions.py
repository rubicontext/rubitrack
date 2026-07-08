"""
Détection de transitions candidates depuis l'historique de lecture
(CurrentlyPlaying, alimenté par le log Icecast pendant les sets).

Deux morceaux joués consécutivement (gap <= MAX_GAP_MINUTES) forment un
enchaînement; s'il revient au moins MIN_OCCURRENCES fois et qu'aucune
transition n'existe encore, il devient une PROPOSITION.

RÈGLE: on ne crée JAMAIS de transition automatiquement. On ne fait que
proposer des candidats; la création se fait au clic sur "Ajouter" (page
set_transitions), après test en live.
"""

import logging
from collections import Counter
from datetime import timedelta

from ..models import CurrentlyPlaying, Transition
from ..playlist.playlist_transitions import get_separator_track_id

logger = logging.getLogger(__name__)

MAX_GAP_MINUTES = 20
MIN_OCCURRENCES = 2


def find_transition_candidates_from_history(min_occurrences: int = MIN_OCCURRENCES) -> list:
    """Analyse l'historique et retourne les enchaînements récurrents PAS ENCORE
    enregistrés comme transitions. Ne crée rien.

    Returns: liste de dicts {source_id, destination_id, occurrences}, triée par
    occurrences décroissantes.
    """
    pair_counts = _count_consecutive_pairs()
    existing = set(Transition.objects.values_list('track_source_id', 'track_destination_id'))
    candidates = [
        {'source_id': source_id, 'destination_id': destination_id, 'occurrences': occurrences}
        for (source_id, destination_id), occurrences in pair_counts.items()
        if occurrences >= min_occurrences and (source_id, destination_id) not in existing
    ]
    candidates.sort(key=lambda c: c['occurrences'], reverse=True)
    logger.info("Transitions candidates trouvées: %d", len(candidates))
    return candidates


def _count_consecutive_pairs() -> Counter:
    """Compte les enchaînements consécutifs (gap <= MAX_GAP, séparateur exclu)
    dans tout l'historique. Utilisé par candidats ET par le calcul de play_count."""
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
            continue
        pair_counts[(prev.track_id, cur.track_id)] += 1
    return pair_counts


def recount_transition_play_counts() -> dict:
    """Met à jour Transition.play_count = nb de fois réellement enchaînée en set.
    NE crée aucune transition; ne fait qu'annoter les transitions existantes.

    Returns: {'transitions', 'played', 'total_plays'}
    """
    pair_counts = _count_consecutive_pairs()
    transitions = list(Transition.objects.all())
    played = 0
    for transition in transitions:
        count = pair_counts.get((transition.track_source_id, transition.track_destination_id), 0)
        if transition.play_count != count:
            transition.play_count = count
            transition.save(update_fields=['play_count'])
        if count > 0:
            played += 1
    stats = {
        'transitions': len(transitions),
        'played': played,
        'total_plays': sum(pair_counts.values()),
    }
    logger.info("Recalcul play_count des transitions: %s", stats)
    return stats
