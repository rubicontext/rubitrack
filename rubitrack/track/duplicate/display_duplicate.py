import logging

from django.contrib import messages
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from ..models import DuplicateCandidate, Track
from .detection import find_duplicate_artists, scan_duplicates, suggest_survivor
from .manual_merge_duplicate import merge_duplicate_tracks

logger = logging.getLogger(__name__)

# Mapping des tonalités enharmoniques équivalentes (bémols <-> dièses)
ENHARMONIC_EQUIVALENTS = {
    'A#': 'Bb', 'Bb': 'A#',
    'A#m': 'Bbm', 'Bbm': 'A#m',
    'C#': 'Db', 'Db': 'C#',
    'C#m': 'Dbm', 'Dbm': 'C#m',
    'D#': 'Eb', 'Eb': 'D#',
    'D#m': 'Ebm', 'Ebm': 'D#m',
    'F#': 'Gb', 'Gb': 'F#',
    'F#m': 'Gbm', 'Gbm': 'F#m',
    'G#': 'Ab', 'Ab': 'G#',
    'G#m': 'Abm', 'Abm': 'G#m',
}


def normalize_key_enharmonic(key: str) -> str:
    """Normalise une tonalité vers sa forme canonique (dièse préféré au bémol)."""
    if not key:
        return key
    return ENHARMONIC_EQUIVALENTS.get(key, key)


def keys_are_equivalent(key_a: str, key_b: str) -> bool:
    """Retourne True si deux tonalités sont enharmoniquement équivalentes."""
    if not key_a or not key_b:
        return False
    return normalize_key_enharmonic(key_a) == normalize_key_enharmonic(key_b)


def _cue_slots(track: Track):
    """Liste des 8 slots avec temps (ou None) pour la comparaison A/B."""
    by_slot = {c.slot: c for c in track.cue_points.all()}
    return [
        by_slot[i].get_time_without_ms() if i in by_slot else None
        for i in range(1, 9)
    ]


# Seules ces raisons justifient un merge automatique (identité de fichier),
# et toujours sous réserve d'absence de conflit de cues (règle absolue)
HARD_REASONS = {'same_audio_id', 'same_file_path'}


def _is_auto_eligible(candidate: DuplicateCandidate) -> bool:
    return (candidate.score == 100
            and not candidate.cue_conflict
            and bool(HARD_REASONS.intersection(candidate.reasons)))


def _candidate_context(candidate: DuplicateCandidate) -> dict:
    survivor = suggest_survivor(candidate.track_a, candidate.track_b)
    ctx = {
        'candidate': candidate,
        'suggested_survivor': survivor,
        'cues_a': candidate.track_a.cue_points.count(),
        'cues_b': candidate.track_b.cue_points.count(),
        'auto_eligible': _is_auto_eligible(candidate),
    }
    if candidate.cue_conflict:
        # REGLE: cues des deux côtés -> jamais d'auto-merge, comparaison 8 slots
        ctx['cue_slots'] = list(zip(
            range(1, 9), _cue_slots(candidate.track_a), _cue_slots(candidate.track_b)
        ))
    return ctx


def display_duplicates(request):
    # Fonction pour le menu principal des duplicatas
    return render(request, 'track/duplicates/duplicates.html')


def manual_merge_track_batch(request):
    """Page principale des doublons: candidats scorés + artistes dupliqués."""
    pending = (
        DuplicateCandidate.objects.filter(status=DuplicateCandidate.STATUS_PENDING)
        .select_related('track_a__artist', 'track_b__artist')
        .prefetch_related('track_a__cue_points', 'track_b__cue_points')
        .order_by('-score', 'id')
    )
    candidates = [_candidate_context(c) for c in pending]
    auto_mergeable = [c for c in candidates if c['auto_eligible']]
    return render(request, 'track/duplicates/manual_merge_track_batch.html', {
        'candidates': candidates,
        'auto_mergeable_count': len(auto_mergeable),
        'dismissed_count': DuplicateCandidate.objects.filter(
            status=DuplicateCandidate.STATUS_DISMISSED).count(),
        'duplicate_artists': find_duplicate_artists(),
    })


@require_POST
def scan_duplicates_view(request):
    stats = scan_duplicates()
    messages.success(
        request,
        f"Scan terminé: {stats['total_found']} paires trouvées "
        f"({stats['created']} nouvelles, {stats['updated']} mises à jour, "
        f"{stats['skipped_memory']} déjà traitées/écartées)."
    )
    return redirect("manual_merge_track_batch")


@require_POST
def merge_candidate(request):
    """Merge un candidat: survivant choisi explicitement dans le formulaire."""
    candidate = DuplicateCandidate.objects.get(
        id=int(request.POST["candidate_id"]),
        status=DuplicateCandidate.STATUS_PENDING,
    )
    survivor_id = int(request.POST["survivor_id"])
    ids = {candidate.track_a_id, candidate.track_b_id}
    if survivor_id not in ids:
        messages.error(request, "Survivant invalide pour ce candidat.")
        return redirect("manual_merge_track_batch")
    loser_id = (ids - {survivor_id}).pop()
    merge_duplicate_tracks(survivor_id, loser_id)
    messages.success(request, f"Fusion OK: #{loser_id} fusionné dans #{survivor_id}.")
    return redirect("manual_merge_track_batch")


@require_POST
def dismiss_candidate(request):
    """Marque un candidat 'pas un doublon' — mémoire persistante, jamais reproposé."""
    updated = DuplicateCandidate.objects.filter(
        id=int(request.POST["candidate_id"]),
        status=DuplicateCandidate.STATUS_PENDING,
    ).update(status=DuplicateCandidate.STATUS_DISMISSED)
    if updated:
        messages.success(request, "Paire écartée définitivement.")
    return redirect("manual_merge_track_batch")


@require_POST
def auto_merge_certain(request):
    """Merge automatique du palier score=100 (audio_id/file_path identiques).

    REGLE ABSOLUE: les paires où les DEUX tracks ont des cue points sont
    exclues — elles restent en manuel avec comparaison des slots.
    """
    eligible = [
        c for c in DuplicateCandidate.objects.filter(
            status=DuplicateCandidate.STATUS_PENDING, score=100, cue_conflict=False,
        ).select_related('track_a', 'track_b')
        if _is_auto_eligible(c)
    ]
    merged = 0
    for candidate in eligible:
        try:
            survivor = suggest_survivor(candidate.track_a, candidate.track_b)
            loser = candidate.track_b if survivor == candidate.track_a else candidate.track_a
            merge_duplicate_tracks(survivor.id, loser.id)
            merged += 1
        except Track.DoesNotExist:
            continue
    messages.success(request, f"Auto-merge: {merged} paires certaines fusionnées "
                              f"(les conflits de cues restent en manuel).")
    return redirect("manual_merge_track_batch")
