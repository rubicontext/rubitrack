from django import forms
from django.shortcuts import render
from ..models import Track, Transition

# Vue pour la page de création manuelle de transition

class ManualTransitionForm(forms.Form):
    track_a = forms.ModelChoiceField(queryset=Track.objects.all().order_by('title'), label="Track A")
    track_b = forms.ModelChoiceField(queryset=Track.objects.all().order_by('title'), label="Track B")
    direction = forms.ChoiceField(choices=[('A_to_B', 'A → B'), ('B_to_A', 'B → A')], label="Direction")
    comment = forms.CharField(required=False, label="Commentaire")

def manual_transition(request):
    tracks = Track.objects.all().order_by('title','artist__name')
    message = None
    
    # Récupérer les paramètres GET pour pré-sélectionner les tracks
    preselected_source = request.GET.get('track_source')
    preselected_destination = request.GET.get('track_destination')
    
    if request.method == "POST":
        # Vérifier si c'est une copie de transitions
        if 'copy_all' in request.POST:
            source_track_id = int(request.POST.get("copy_source_id"))
            dest_track_id = int(request.POST.get("copy_dest_id"))
            source_track = Track.objects.get(id=source_track_id)
            dest_track = Track.objects.get(id=dest_track_id)
            
            # Copier toutes les transitions sortantes (track source)
            outgoing_transitions = Transition.objects.filter(track_source=source_track)
            copied_count = 0
            for trans in outgoing_transitions:
                # Vérifier si la transition n'existe pas déjà
                if not Transition.objects.filter(
                    track_source=dest_track, 
                    track_destination=trans.track_destination
                ).exists():
                    Transition.objects.create(
                        track_source=dest_track,
                        track_destination=trans.track_destination,
                        comment=trans.comment,
                        ranking=trans.ranking,
                        transition_type=trans.transition_type
                    )
                    copied_count += 1
            
            # Copier toutes les transitions entrantes (track destination)
            incoming_transitions = Transition.objects.filter(track_destination=source_track)
            for trans in incoming_transitions:
                # Vérifier si la transition n'existe pas déjà
                if not Transition.objects.filter(
                    track_source=trans.track_source, 
                    track_destination=dest_track
                ).exists():
                    Transition.objects.create(
                        track_source=trans.track_source,
                        track_destination=dest_track,
                        comment=trans.comment,
                        ranking=trans.ranking,
                        transition_type=trans.transition_type
                    )
                    copied_count += 1
            
            message = f"✓ {copied_count} transitions copiées de '{source_track.title}' vers '{dest_track.title}'"
        else:
            # Code existant pour créer une seule transition
            track1_id = int(request.POST.get("track1_id"))
            track2_id = int(request.POST.get("track2_id"))
            direction = request.POST.get("direction")
            comment = request.POST.get("comment", "")
            track1 = Track.objects.get(id=track1_id)
            track2 = Track.objects.get(id=track2_id)
            
            # Déterminer source et destination selon la direction
            if direction == "right":
                source_track = track1
                dest_track = track2
            else:
                source_track = track2
                dest_track = track1
            
            # Vérifier si la transition existe déjà
            if Transition.objects.filter(track_source=source_track, track_destination=dest_track).exists():
                message = f"error:Transition already exists: {source_track.title} → {dest_track.title}"
            else:
                Transition.objects.create(track_source=source_track, track_destination=dest_track, comment=comment)
                message = f"Transition enregistrée : {source_track.title} → {dest_track.title}"
    
    return render(request, 'track/currently_playing/manual_transition.html', {
        'tracks': tracks,
        'message': message,
        'preselected_source': preselected_source,
        'preselected_destination': preselected_destination,
    })
