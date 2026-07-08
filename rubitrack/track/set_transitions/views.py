"""
Transitions de sets — PROPOSITIONS uniquement.

Règle absolue: on ne crée JAMAIS de transition automatiquement. Cette page
liste les enchaînements récurrents détectés dans l'historique de sets qui ne
sont pas encore des transitions, avec un bouton "Ajouter" par ligne. La
création se fait uniquement au clic, après que le DJ ait testé en live.
"""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from ..currently_playing.auto_transitions import find_transition_candidates_from_history
from ..currently_playing.transition import create_transition
from ..models import Track

logger = logging.getLogger(__name__)

ADDED_FROM_SET_COMMENT = 'Ajoutée depuis les sets'


@login_required
def set_transitions_view(request):
    """Liste les transitions candidates (enchaînements récurrents non enregistrés)."""
    candidates = find_transition_candidates_from_history()
    ids = {c['source_id'] for c in candidates} | {c['destination_id'] for c in candidates}
    tracks = {t.id: t for t in Track.objects.filter(id__in=ids).select_related('artist')}

    rows = []
    for c in candidates:
        source = tracks.get(c['source_id'])
        destination = tracks.get(c['destination_id'])
        if not source or not destination:
            continue
        bpm_delta = None
        if source.bpm and destination.bpm:
            bpm_delta = round((destination.bpm - source.bpm) / source.bpm * 100, 1)
        rows.append({
            'source': source,
            'destination': destination,
            'occurrences': c['occurrences'],
            'bpm_delta': bpm_delta,
        })

    return render(request, 'track/set_transitions/set_transitions.html', {'rows': rows})


@login_required
@require_POST
def add_set_transition(request):
    """Crée UNE transition, uniquement sur clic explicite du bouton Ajouter."""
    source_id = request.POST.get('source_id')
    destination_id = request.POST.get('destination_id')
    transition = create_transition(source_id, destination_id, ADDED_FROM_SET_COMMENT)
    if transition:
        messages.success(
            request,
            f"Transition ajoutée : {transition.track_source.title} → "
            f"{transition.track_destination.title}."
        )
    else:
        messages.error(request, "Impossible de créer la transition.")
    return redirect('set_transitions')
