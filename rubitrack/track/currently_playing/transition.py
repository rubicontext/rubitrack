from ..models import Transition, TransitionType, Track


def create_transition(trackSourceId, trackDestinationId, comment):
    transition = Transition()
    transition.track_source = Track.objects.get(id=trackSourceId)
    transition.track_destination = Track.objects.get(id=trackDestinationId)
    transition.comment = comment
    transition.transition_type = TransitionType.objects.get(id=1)
    transition.save()
    return transition


def delete_transition(transitionId):
    transition = Transition.objects.get(id=transitionId)
    transition.delete()
