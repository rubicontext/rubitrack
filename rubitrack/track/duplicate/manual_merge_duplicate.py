import logging

from django import forms
from django.db import transaction
from django.shortcuts import render, redirect

from ..models import (
    CurrentlyPlaying, MergeLog, PlaylistTrack, Track, Transition,
)

logger = logging.getLogger(__name__)


class TrackChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.title.lstrip()} - {obj.artist.name} ({obj.id})"


class ManualMergeForm(forms.Form):
    track_a = TrackChoiceField(queryset=Track.objects.all().order_by('title'), label="Track to keep (A)")
    track_b = TrackChoiceField(queryset=Track.objects.all().order_by('title'), label="Track to delete (B)")


# Champs simples repris du donneur quand le survivant n'a pas de valeur
COALESCE_FIELDS = (
    'comment', 'comment2', 'audio_id', 'file_path', 'file_name', 'location_dir',
    'musical_key', 'bpm', 'bitrate', 'playtime', 'energy', 'genre',
)


def _snapshot_track(track: Track) -> dict:
    """Snapshot JSON-compatible de la track avant suppression (audit/undo)."""
    return {
        'id': track.id,
        'title': track.title,
        'artist': track.artist.name if track.artist else None,
        'fields': {
            f: (str(getattr(track, f)) if getattr(track, f) is not None else None)
            for f in COALESCE_FIELDS + ('ranking', 'playcount', 'date_last_played')
            if f != 'genre'
        },
        'genre': track.genre.name if track.genre else None,
        'cue_points': [
            {'slot': c.slot, 'time': c.time, 'time_ms': str(c.time_ms) if c.time_ms is not None else None,
             'len_ms': str(c.len_ms) if c.len_ms is not None else None, 'traktor_type': c.traktor_type}
            for c in track.cue_points.all()
        ],
        'transition_ids': list(
            Transition.objects.filter(track_source=track).values_list('id', flat=True)
        ) + list(
            Transition.objects.filter(track_destination=track).values_list('id', flat=True)
        ),
        'playlist_ids': list(track.playlist_entries.values_list('playlist_id', flat=True)),
    }


@transaction.atomic
def merge_duplicate_tracks(track_a_id: int, track_b_id: int):
    """Fusionne B (supprimé) dans A (survivant), sans perte:
    - champs simples: coalesce (A prioritaire), playcount = somme,
      ranking / date_last_played = max
    - cue points: union PAR SLOT (les slots vides de A sont comblés par B)
    - transitions / playlists / CurrentlyPlaying: réaffectés à A
    - MergeLog: snapshot de B (les DuplicateCandidate impliquant B partent en cascade)
    """
    track_a = Track.objects.get(id=track_a_id)
    track_b = Track.objects.get(id=track_b_id)

    log_entry = MergeLog.objects.create(
        survivor=track_a,
        deleted_track_id=track_b.id,
        deleted_snapshot=_snapshot_track(track_b),
    )

    # --- Champs simples
    for field in COALESCE_FIELDS:
        if not getattr(track_a, field) and getattr(track_b, field):
            setattr(track_a, field, getattr(track_b, field))
    track_a.playcount = (track_a.playcount or 0) + (track_b.playcount or 0)
    track_a.ranking = max(track_a.ranking or 0, track_b.ranking or 0) or None
    if track_b.date_last_played and (
        not track_a.date_last_played or track_b.date_last_played > track_a.date_last_played
    ):
        track_a.date_last_played = track_b.date_last_played
    track_a.save()

    # --- Cue points: union par slot (A garde les siens, B comble les trous)
    slots_a = set(track_a.cue_points.values_list('slot', flat=True))
    moved_slots = []
    for cue in track_b.cue_points.all():
        if cue.slot in slots_a:
            cue.delete()
        else:
            cue.track = track_a
            cue.save()
            moved_slots.append(cue.slot)
    if moved_slots:
        logger.info("Merge #%s->#%s: cues de B repris sur slots %s", track_b_id, track_a_id, moved_slots)

    # --- Transitions (sans doublon, en conservant type/ranking/commentaire)
    for t in Transition.objects.filter(track_source=track_b).exclude(track_destination=track_a):
        Transition.objects.get_or_create(
            track_source=track_a, track_destination=t.track_destination,
            defaults={'comment': t.comment, 'transition_type': t.transition_type, 'ranking': t.ranking},
        )
    for t in Transition.objects.filter(track_destination=track_b).exclude(track_source=track_a):
        Transition.objects.get_or_create(
            track_source=t.track_source, track_destination=track_a,
            defaults={'comment': t.comment, 'transition_type': t.transition_type, 'ranking': t.ranking},
        )

    # --- Historique de lecture: réaffectation par FK
    CurrentlyPlaying.objects.filter(track=track_b).update(track=track_a)

    # --- Playlists: B remplacé par A à la même position
    for entry in PlaylistTrack.objects.filter(track=track_b):
        if PlaylistTrack.objects.filter(playlist_id=entry.playlist_id, track=track_a).exists():
            entry.delete()
        else:
            entry.track = track_a
            entry.save()

    # --- Suppression de B (les DuplicateCandidate impliquant B partent en CASCADE;
    # l'historique de la fusion est porté par MergeLog)
    track_b.delete()
    logger.info("Merge termine: #%s supprime, survivant #%s (MergeLog %s)", track_b_id, track_a_id, log_entry.id)


def manual_merge_duplicate(request):
    manual_merge_form = ManualMergeForm()
    if request.method == "POST":
        form = ManualMergeForm(request.POST)
        if form.is_valid():
            track_a = form.cleaned_data["track_a"]
            track_b = form.cleaned_data["track_b"]
            merge_duplicate_tracks(track_a.id, track_b.id)
            return redirect("manual_merge_track")
    return render(request, 'track/duplicates/manual_merge_track.html', {'manual_merge_form': manual_merge_form})
