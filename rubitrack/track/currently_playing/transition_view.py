from track.models import Transition
from track.currently_playing.transition import create_transition

from .currently_playing import get_more_transition_block, get_more_transition_block_history
import logging

logger = logging.getLogger(__name__)

def is_context_history(request):
    """Check if the request context is history or playing"""
    history = request.GET.get('history')
    return history is not None and history == 'true'

def add_new_transition(request):
    trackSourceId = request.GET['trackSourceId']
    trackDestinationId = request.GET['trackDestinationId']
    transition = create_transition(trackSourceId, trackDestinationId, 'Added!')
    logger.info('Transition ADDED  %s %s %s', transition.track_source.title, '/', transition.track_destination.title)

    if is_context_history(request):
        currentTrackId = request.GET['currentTrackId']
        return get_more_transition_block_history(request, currentTrackId)

    return get_more_transition_block(request)


def delete_transition(request):
    transitionId = request.GET['transitionDeleteId']
    transition = Transition.objects.get(id=transitionId)
    transition.delete()

    # get context history or playing
    if is_context_history(request):
        currentTrackId = request.GET['currentTrackId']
        return get_more_transition_block_history(request, currentTrackId)

    return get_more_transition_block(request)


def update_transition_comment(request):
    transitionId = request.GET['transitionUpdateId']
    newComment = request.GET['newComment']
    logger.info('transition to update from req ID= %s', transitionId)
    transition = Transition.objects.get(id=transitionId)
    transition.comment = newComment
    transition.save()

    # get context history or playing
    if is_context_history(request):
        currentTrackId = request.GET['currentTrackId']
        return get_more_transition_block_history(request, currentTrackId)

    return get_more_transition_block(request)
