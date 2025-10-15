from ..models import Transition
from .transitions_core import create_transition
from ..currently_playing.currently_playing import get_more_transition_block, get_more_transition_block_history

def is_context_history(request):
    """Check if the request context is history or playing"""
    history = request.GET.get('history')
    return history is not None and history == 'true'

def add_new_transition(request):
    track_source_id = request.GET['trackSourceId']  # param name kept for frontend compatibility
    track_destination_id = request.GET['trackDestinationId']
    transition = create_transition(track_source_id, track_destination_id, 'Added!')
    if transition:
        print('Transition ADDED ', transition.track_source.title, '/', transition.track_destination.title)

    if is_context_history(request):
        current_track_id = request.GET.get('currentTrackId')
        return get_more_transition_block_history(request, current_track_id)

    return get_more_transition_block(request)


def delete_transition(request):
    transition_id = request.GET['transitionDeleteId']
    Transition.objects.filter(id=transition_id).delete()

    if is_context_history(request):
        current_track_id = request.GET.get('currentTrackId')
        return get_more_transition_block_history(request, current_track_id)

    return get_more_transition_block(request)


def update_transition_comment(request):
    transition_id = request.GET['transitionUpdateId']
    new_comment = request.GET['newComment']
    print("transition to update from req ID=", transition_id)
    try:
        transition = Transition.objects.get(id=transition_id)
        transition.comment = new_comment
        transition.save()
    except Transition.DoesNotExist:
        print(f"Transition {transition_id} introuvable")

    if is_context_history(request):
        current_track_id = request.GET.get('currentTrackId')
        return get_more_transition_block_history(request, current_track_id)

    return get_more_transition_block(request)
