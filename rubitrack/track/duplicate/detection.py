"""
Moteur de détection des doublons — alimente DuplicateCandidate par paliers:
  T1 (100) : même audio_id ou même file_path (quasi-certitude)
  T2 (95)  : même artiste + même titre-base (suffixe " - Clé - Note" retiré)
  T3 (90+) : rapidfuzz token_sort sur "artiste titre-base", garde-fou durée

Les candidats 'dismissed'/'merged' ne sont jamais recréés (mémoire persistante).
"""

import logging
import re
from collections import defaultdict
from typing import Dict, List, Tuple

from rapidfuzz import fuzz, process

from ..models import DuplicateCandidate, Track

logger = logging.getLogger(__name__)

# "Titre - Am - 6" / "Titre - A#m - 12" -> "Titre" (clé + note en fin de titre)
TITLE_SUFFIX_RE = re.compile(r"\s*-\s*[A-G](?:[#b♯♭]?m?|m)\s*-\s*\d{1,2}\s*$", re.IGNORECASE)

FUZZY_MIN_SCORE = 90
DURATION_TOLERANCE_SECONDS = 5


def normalize_title_base(title: str) -> str:
    """Titre sans le suffixe clé/note, espaces normalisés, casse repliée."""
    base = TITLE_SUFFIX_RE.sub('', title or '').strip()
    return re.sub(r'\s+', ' ', base).lower()


def _duration_compatible(track_a: Track, track_b: Track) -> bool:
    if not track_a.playtime or not track_b.playtime:
        return True  # durée inconnue: on ne bloque pas, le score parle
    return abs(track_a.playtime - track_b.playtime) <= DURATION_TOLERANCE_SECONDS


def _canonical(track_a: Track, track_b: Track) -> Tuple[Track, Track]:
    return (track_a, track_b) if track_a.id < track_b.id else (track_b, track_a)


def scan_duplicates() -> dict:
    """Scanne toute la collection et met à jour la table DuplicateCandidate.

    Returns: stats du scan {created, updated, skipped_dismissed, pairs_by_reason}.
    """
    tracks = list(
        Track.objects.select_related('artist').prefetch_related('cue_points').all()
    )
    has_cues: Dict[int, bool] = {t.id: bool(len(t.cue_points.all())) for t in tracks}

    # (id_a, id_b) -> {'score': int, 'reasons': [str]}
    found: Dict[Tuple[int, int], dict] = {}

    def add_pair(track_a: Track, track_b: Track, score: int, reason: str):
        a, b = _canonical(track_a, track_b)
        entry = found.setdefault((a.id, b.id), {'score': 0, 'reasons': []})
        entry['score'] = max(entry['score'], score)
        if reason not in entry['reasons']:
            entry['reasons'].append(reason)

    # --- T1: identifiants forts
    by_audio_id: Dict[str, List[Track]] = defaultdict(list)
    by_file_path: Dict[str, List[Track]] = defaultdict(list)
    for t in tracks:
        if t.audio_id:
            by_audio_id[t.audio_id].append(t)
        if t.file_path:
            by_file_path[t.file_path.lower()].append(t)
    for group in by_audio_id.values():
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                add_pair(group[i], group[j], 100, 'same_audio_id')
    for group in by_file_path.values():
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                add_pair(group[i], group[j], 100, 'same_file_path')

    # --- T2: même artiste + même titre-base
    by_artist_base: Dict[Tuple[int, str], List[Track]] = defaultdict(list)
    for t in tracks:
        base = normalize_title_base(t.title)
        if base:
            by_artist_base[(t.artist_id, base)].append(t)
    for group in by_artist_base.values():
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                if _duration_compatible(group[i], group[j]):
                    add_pair(group[i], group[j], 95, 'same_title_base')

    # --- T3: fuzzy sur "artiste titre-base" (durée compatible exigée)
    strings = [
        f"{t.artist.name if t.artist else ''} {normalize_title_base(t.title)}".strip().lower()
        for t in tracks
    ]
    matrix = process.cdist(
        strings, strings, scorer=fuzz.token_sort_ratio,
        score_cutoff=FUZZY_MIN_SCORE, workers=-1,
    )
    n = len(tracks)
    for i in range(n):
        row = matrix[i]
        for j in range(i + 1, n):
            score = int(row[j])
            if score >= FUZZY_MIN_SCORE and _duration_compatible(tracks[i], tracks[j]):
                add_pair(tracks[i], tracks[j], score, f'fuzzy:{score}')

    # --- Upsert en respectant la mémoire (dismissed/merged intouchables)
    existing = {
        (c.track_a_id, c.track_b_id): c
        for c in DuplicateCandidate.objects.filter(
            track_a_id__in=[a for a, _ in found] or [0]
        )
    }
    stats = {'created': 0, 'updated': 0, 'skipped_memory': 0, 'total_found': len(found)}
    for (a_id, b_id), data in found.items():
        cue_conflict = has_cues.get(a_id, False) and has_cues.get(b_id, False)
        candidate = existing.get((a_id, b_id))
        if candidate is None:
            candidate = DuplicateCandidate.objects.filter(track_a_id=a_id, track_b_id=b_id).first()
        if candidate:
            if candidate.status != DuplicateCandidate.STATUS_PENDING:
                stats['skipped_memory'] += 1
                continue
            if (candidate.score != data['score'] or candidate.reasons != data['reasons']
                    or candidate.cue_conflict != cue_conflict):
                candidate.score = data['score']
                candidate.reasons = data['reasons']
                candidate.cue_conflict = cue_conflict
                candidate.save()
                stats['updated'] += 1
        else:
            DuplicateCandidate.objects.create(
                track_a_id=a_id, track_b_id=b_id,
                score=data['score'], reasons=data['reasons'],
                cue_conflict=cue_conflict,
            )
            stats['created'] += 1

    logger.info("Scan doublons: %s", stats)
    return stats


def find_duplicate_artists() -> List[List]:
    """Groupes d'artistes identiques après trim/casse (fragmentation des fiches)."""
    from ..models import Artist
    groups: Dict[str, List] = defaultdict(list)
    for artist in Artist.objects.all():
        groups[artist.name.strip().lower()].append(artist)
    return [g for g in groups.values() if len(g) > 1]


def suggest_survivor(track_a: Track, track_b: Track) -> Track:
    """Suggère le survivant: a des cues > playcount > le plus ancien id."""
    cues_a, cues_b = track_a.cue_points.exists(), track_b.cue_points.exists()
    if cues_a != cues_b:
        return track_a if cues_a else track_b
    pc_a, pc_b = track_a.playcount or 0, track_b.playcount or 0
    if pc_a != pc_b:
        return track_a if pc_a > pc_b else track_b
    return track_a if track_a.id < track_b.id else track_b
