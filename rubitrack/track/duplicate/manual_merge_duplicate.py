from django.shortcuts import render, redirect
from ..models import Track, Transition, CurrentlyPlaying, PlaylistTrack
from django import forms
import logging

logger = logging.getLogger(__name__)

class TrackChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.title.lstrip()} - {obj.artist.name} ({obj.id})"

class ManualMergeForm(forms.Form):
    track_a = TrackChoiceField(queryset=Track.objects.all().order_by('title'), label="Track to keep (A)")
    track_b = TrackChoiceField(queryset=Track.objects.all().order_by('title'), label="Track to delete (B)")

def merge_duplicate_tracks(track_a_id: int, track_b_id: int):
    track_a = Track.objects.get(id=track_a_id)
    track_b = Track.objects.get(id=track_b_id)
    
    # Si A n'a pas de commentaire mais B en a un, copier le commentaire de B vers A
    if track_b.comment and track_b.comment.strip() and (not track_a.comment or not track_a.comment.strip()):
        track_a.comment = track_b.comment
        logger.info(f"📝 Commentaire copié de B vers A: '{track_a.comment}'")

    # Si A n'a pas d'audio_id mais B en a un, copier l'audio_id de B vers A
    # Cela évite qu'un prochain import recrée B comme une nouvelle track
    if track_b.audio_id and not track_a.audio_id:
        track_a.audio_id = track_b.audio_id
        logger.info(f"🆔 audio_id copié de B vers A: '{track_a.audio_id}'")

    # Si A n'a pas de file_path mais B en a un, copier aussi
    if track_b.file_path and not track_a.file_path:
        track_a.file_path = track_b.file_path
        logger.info(f"📁 file_path copié de B vers A: '{track_a.file_path}'")

    track_a.save()
    
    # Copier toutes les transitions de B vers A
    for t in Transition.objects.filter(track_source=track_b):
        Transition.objects.get_or_create(track_source=track_a, track_destination=t.track_destination, defaults={"comment": t.comment})
    for t in Transition.objects.filter(track_destination=track_b):
        Transition.objects.get_or_create(track_source=t.track_source, track_destination=track_a, defaults={"comment": t.comment})
    
    # Merge cue points: A garde les siens; ceux de B ne sont repris que si A n'en a pas
    if track_b.cue_points.exists():
        if track_a.cue_points.exists():
            track_b.cue_points.all().delete()
        else:
            track_b.cue_points.update(track=track_a)
    
    # Remplacer B par A dans CurrentlyPlaying
    CurrentlyPlaying.objects.filter(track__title=track_b.title.strip(), track__artist=track_b.artist).update(track=track_a)
    
    # Mettre à jour les playlists: B remplacé par A à la même position
    # (si la playlist contient déjà A, l'entrée de B est simplement supprimée)
    for entry in PlaylistTrack.objects.filter(track=track_b):
        if PlaylistTrack.objects.filter(playlist_id=entry.playlist_id, track=track_a).exists():
            entry.delete()
        else:
            entry.track = track_a
            entry.save()

    # Supprimer la track B
    track_b.delete()

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
