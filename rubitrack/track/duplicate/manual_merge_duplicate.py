from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from ..models import Track, Transition, CurrentlyPlaying, Playlist
from django import forms
import ast

class TrackChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.title.lstrip()} - {obj.artist.name} ({obj.id})"

class ManualMergeForm(forms.Form):
    track_a = TrackChoiceField(queryset=Track.objects.all().order_by('title'), label="Track to keep (A)")
    track_b = TrackChoiceField(queryset=Track.objects.all().order_by('title'), label="Track to delete (B)")

def merge_duplicate_tracks(track_a_id: int, track_b_id: int):
    track_a = Track.objects.get(id=track_a_id)
    track_b = Track.objects.get(id=track_b_id)
    
    # Copier toutes les transitions de B vers A
    for t in Transition.objects.filter(track_source=track_b):
        Transition.objects.get_or_create(track_source=track_a, track_destination=t.track_destination, defaults={"comment": t.comment})
    for t in Transition.objects.filter(track_destination=track_b):
        Transition.objects.get_or_create(track_source=t.track_source, track_destination=track_a, defaults={"comment": t.comment})
    
    # Remplacer B par A dans CurrentlyPlaying
    CurrentlyPlaying.objects.filter(track__title=track_b.title.strip(), track__artist=track_b.artist).update(track=track_a)
    
    # Mettre à jour les playlists - ManyToManyField
    for playlist in Playlist.objects.filter(tracks=track_b):
        playlist.tracks.remove(track_b)
        playlist.tracks.add(track_a)
    
    # Mettre à jour les playlists - track_ids field
    for playlist in Playlist.objects.all():
        if playlist.track_ids:
            try:
                # Parse the track_ids field (Python list format)
                track_ids = ast.literal_eval(playlist.track_ids)
                if isinstance(track_ids, list) and track_b_id in track_ids:
                    # Replace track_b_id with track_a_id
                    updated_ids = [track_a_id if tid == track_b_id else tid for tid in track_ids]
                    playlist.track_ids = str(updated_ids)
                    playlist.save()
            except (ValueError, SyntaxError):
                # Skip playlists with invalid track_ids format
                print(f"Warning: Invalid track_ids format in playlist {playlist.name}")
                continue
    
    # Supprimer la track B
    track_b.delete()

@csrf_exempt
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
