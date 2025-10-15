from ..models import Transition, TransitionType, Track


def create_transition(trackSourceId, trackDestinationId, comment):
    try:
        track_source = Track.objects.get(id=trackSourceId)
        track_destination = Track.objects.get(id=trackDestinationId)
        
        transition = Transition()
        transition.track_source = track_source
        transition.track_destination = track_destination
        transition.comment = comment
        transition.transition_type = TransitionType.objects.get(id=1)
        transition.save()
        return transition
    except Track.DoesNotExist:
        print(f"Erreur: Track avec ID {trackSourceId} ou {trackDestinationId} n'existe pas")
        return None
    except Exception as e:
        print(f"Erreur lors de la création de la transition: {e}")
        return None


def delete_transition(transitionId):
    transition = Transition.objects.get(id=transitionId)
    transition.delete()
