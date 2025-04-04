
from track.models import Transition
from track.transition import create_transition

from .currently_playing import (get_more_transition_block,
                                get_more_transition_block_history)

# ADD NEW TRANSITION
def add_new_transition(request):
    trackSourceId = request.GET['trackSourceId']
    trackDestinationId = request.GET['trackDestinationId']
    transition = create_transition(trackSourceId, trackDestinationId, 'Added!')
    print('Transition ADDED ', transition.track_source.title, '/', transition.track_destination.title)

    # get context history or playing
    history = request.GET['history']
    if history is not None and history == 'true':
        currentTrackId = request.GET['currentTrackId']
        return get_more_transition_block_history(request, currentTrackId)

    return get_more_transition_block(request)


# DELETE TRANSITION
def delete_transition(request):
    transitionId = request.GET['transitionDeleteId']
    transition = Transition.objects.get(id=transitionId)
    transition.delete()

    # get context history or playing
    history = request.GET['history']
    if history is not None and history == 'true':
        currentTrackId = request.GET['currentTrackId']
        return get_more_transition_block_history(request, currentTrackId)

    return get_more_transition_block(request)


# UPDATE TRANSITION
def update_transition_comment(request):
    transitionId = request.GET['transitionUpdateId']
    newComment = request.GET['newComment']
    print("transition to update from req ID=", transitionId)
    transition = Transition.objects.get(id=transitionId)
    transition.comment = newComment
    transition.save()

    # get context history or playing
    history = request.GET['history']
    if history is not None and history == 'true':
        currentTrackId = request.GET['currentTrackId']
        return get_more_transition_block_history(request, currentTrackId)

    return get_more_transition_block(request)
