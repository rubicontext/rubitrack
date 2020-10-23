from django.http import HttpResponse
from .models import Transition, TransitionType, Track
from .currently_playing import display_currently_playing, get_more_transition_before_block

#ADD NEW TRANSITION
def add_new_transition(request):
	trackSourceId = request.GET['trackSourceId']
	trackDestinationId = request.GET['trackDestinationId']
	transition=Transition()
	transition.track_source=Track.objects.get(id=trackSourceId)
	transition.track_destination=Track.objects.get(id=trackDestinationId)
	transition.comment='Added automatically'
	transition.transition_type=TransitionType.objects.get(id=1)
	transition.save()
	#return(display_currently_playing(request))

	#return the previous transition block for display
	return(get_more_transition_before_block(request))

#DELETE TRANSITION
def delete_transition(request):
	transitionId = request.GET['transitionDeleteId']
	transition=Transition.objects.get(id=transitionId)
	transition.delete()
	return(display_currently_playing(request))



