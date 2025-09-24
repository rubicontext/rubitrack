from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from ..models import Track, Artist, Transition, CurrentlyPlaying
from django import forms

class ArtistChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.name} ({obj.id})"

class ManualMergeArtistForm(forms.Form):
    artist_a = ArtistChoiceField(queryset=Artist.objects.all().order_by('name'), label="Artist to keep (A)")
    artist_b = ArtistChoiceField(queryset=Artist.objects.all().order_by('name'), label="Artist to delete (B)")

def merge_duplicate_artists(artist_a_id: int, artist_b_id: int):
    """
    Merge artist B into artist A:
    - All tracks from artist B are reassigned to artist A
    - All transitions involving tracks from artist B are updated
    - CurrentlyPlaying entries are updated
    - Artist B is deleted
    """
    artist_a = Artist.objects.get(id=artist_a_id)
    artist_b = Artist.objects.get(id=artist_b_id)
    
    print(f"Merging artist '{artist_b.name}' into '{artist_a.name}'")
    
    # Get all tracks from artist B
    tracks_b = Track.objects.filter(artist=artist_b)
    
    # Reassign all tracks from artist B to artist A
    for track in tracks_b:
        track.artist = artist_a
        track.save()
    
    # Delete artist B (tracks are now reassigned, so this should be safe)
    artist_b.delete()
    print(f"Deleted artist '{artist_b.name}'")

@csrf_exempt
def manual_merge_artist(request):
    manual_merge_form = ManualMergeArtistForm()
    if request.method == "POST":
        form = ManualMergeArtistForm(request.POST)
        if form.is_valid():
            artist_a = form.cleaned_data["artist_a"]
            artist_b = form.cleaned_data["artist_b"]
            
            # Safety check: prevent merging an artist with itself
            if artist_a.id == artist_b.id:
                form.add_error(None, "Cannot merge an artist with itself")
                return render(request, 'track/manual_merge_artist.html', {'manual_merge_form': form})
            
            merge_duplicate_artists(artist_a.id, artist_b.id)
            return redirect("manual_merge_artist")
    
    return render(request, 'track/manual_merge_artist.html', {'manual_merge_form': manual_merge_form})
