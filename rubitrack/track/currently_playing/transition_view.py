import logging

from django.views.decorators.http import require_POST

from track.models import Transition
from track.currently_playing.transition import create_transition

from .currently_playing import get_more_transition_block, get_more_transition_block_history

logger = logging.getLogger(__name__)


def is_context_history(request):
    """Check if the request context is history or playing"""
    history = request.POST.get('history')
    return history is not None and history == 'true'


@require_POST
def add_new_transition(request):
    trackSourceId = request.POST['trackSourceId']
    trackDestinationId = request.POST['trackDestinationId']
    transition = create_transition(trackSourceId, trackDestinationId, 'Added!')
    if transition:
        logger.info('Transition ADDED  %s / %s', transition.track_source.title, transition.track_destination.title)

    if is_context_history(request):
        currentTrackId = request.POST['currentTrackId']
        return get_more_transition_block_history(request, currentTrackId)

    return get_more_transition_block(request)


@require_POST
def delete_transition(request):
    transitionId = request.POST['transitionDeleteId']
    transition = Transition.objects.get(id=transitionId)
    transition.delete()

    # get context history or playing
    if is_context_history(request):
        currentTrackId = request.POST['currentTrackId']
        return get_more_transition_block_history(request, currentTrackId)

    return get_more_transition_block(request)


@require_POST
def update_transition_comment(request):
    transitionId = request.POST['transitionUpdateId']
    newComment = request.POST['newComment']
    logger.info('transition to update from req ID= %s', transitionId)
    transition = Transition.objects.get(id=transitionId)
    transition.comment = newComment
    transition.save()

    # get context history or playing
    if is_context_history(request):
        currentTrackId = request.POST['currentTrackId']
        return get_more_transition_block_history(request, currentTrackId)

    return get_more_transition_block(request)
