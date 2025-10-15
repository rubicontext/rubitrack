from django import forms
from django.shortcuts import render, redirect
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
    if request.method == "POST":
        track1_id = int(request.POST.get("track1_id"))
        track2_id = int(request.POST.get("track2_id"))
        direction = request.POST.get("direction")
        comment = request.POST.get("comment", "")
        track1 = Track.objects.get(id=track1_id)
        track2 = Track.objects.get(id=track2_id)
        if direction == "right":
            Transition.objects.create(track_source=track1, track_destination=track2, comment=comment)
            message = f"Transition enregistrée : {track1.title} → {track2.title}"
        else:
            Transition.objects.create(track_source=track2, track_destination=track1, comment=comment)
            message = f"Transition enregistrée : {track2.title} → {track1.title}"
    return render(request, 'track/currently_playing/manual_transition.html', {
        'tracks': tracks,
        'message': message,
    })
