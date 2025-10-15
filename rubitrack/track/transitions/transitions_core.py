"""Transition domain core helpers (renamed from core.py)"""
from ..models import Transition, TransitionType, Track


def create_transition(track_source_id, track_destination_id, comment):
    try:
        track_source = Track.objects.get(id=track_source_id)
        track_destination = Track.objects.get(id=track_destination_id)
        transition = Transition(
            track_source=track_source,
            track_destination=track_destination,
            comment=comment,
            transition_type=TransitionType.objects.get(id=1),
        )
        transition.save()
        return transition
    except Track.DoesNotExist:
        print(f"Erreur: Track avec ID {track_source_id} ou {track_destination_id} n'existe pas")
        return None
    except Exception as e:
        print(f"Erreur lors de la création de la transition: {e}")
        return None


def delete_transition(transition_id):
    Transition.objects.filter(id=transition_id).delete()
