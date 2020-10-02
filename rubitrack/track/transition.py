from django.http import HttpResponse
from .models import Transition, TransitionType, Track
from .currently_playing import display_currently_playing

#ADD NEW TRANSITION
def add_new_transition(request):
	trackId = request.GET['trackId']
	destinationId = request.GET['destinationId']
	transition=Transition()
	transition.track_source=Track.objects.get(id=trackId)
	transition.track_destination=Track.objects.get(id=destinationId)
	transition.comment='Added automatically'
	transition.transition_type=TransitionType.objects.get(id=1)
	transition.save()

	return(display_currently_playing(request))

#DELETE TRANSITION
def delete_transition(request):
	transitionId = request.GET['transitionDeleteId']
	transition=Transition.objects.get(id=transitionId)
	transition.delete()
	return(display_currently_playing(request))