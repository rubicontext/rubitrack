import os
import string

from django.shortcuts import render
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from track.currently_playing.transition import create_transition

from ..models import Config, Transition, Playlist
import logging

logger = logging.getLogger(__name__)

PLAYLIST_TRANSITION_AUTO_GENERATED = 'Generated from Playlist : '


def get_separator_track_id() -> int:
    """ID de la track séparateur (configurable, propre à chaque instance)."""
    return Config.get_config().separator_track_id


def get_waveform_url_for_track(track):
    """
    Get the waveform URL for a given track if it exists
    Returns None if waveform file doesn't exist
    """
    waveform_filename = f'waveform_track_{track.id}.png'
    waveform_path = os.path.join(settings.MEDIA_ROOT, 'waveforms', waveform_filename)
    if os.path.exists(waveform_path):
        return f"{settings.MEDIA_URL}waveforms/{waveform_filename}"
    return None


@login_required
def display_playlist_transitions(request, PlaylistId):
    currentPlaylist = Playlist.objects.get(id=PlaylistId)
    if currentPlaylist is None:
        return render(
            request,
            'track/playlists/playlist_transitions.html',
            {
                'currentPlaylist': None,
                'playlistTransitions': None,
                'plylistTracks': None,
            },
        )

    else:
        playlistTransitions = get_transitions_from_playlist(currentPlaylist)
        playlistTracks = get_ordered_tracks_from_playlist(currentPlaylist)

        # Add waveform URLs to transitions
        transitions_with_waveforms = []
        for transition in playlistTransitions:
            waveform_url = get_waveform_url_for_track(transition.track_source)
            transitions_with_waveforms.append({
                'transition': transition,
                'waveform_url': waveform_url
            })

        logger.info('All transitions for playlist :  %s', currentPlaylist)
        return render(
            request,
            'track/playlists/playlist_transitions.html',
            {
                'currentPlaylist': currentPlaylist,
                'playlistTransitions': playlistTransitions,
                'playlistTracks': playlistTracks,
                'firstTrack': playlistTracks[0],
                'transitions_with_waveforms': transitions_with_waveforms,
            },
        )


def get_transitions_from_playlist(current_playlist: Playlist):
    if not current_playlist:
        return []
    track_ids = get_track_ids_from_playlist(current_playlist)
    if len(track_ids) < 2:
        return []

    transitions = []
    for index_track_id in range(len(track_ids)-1):
        track_source_id = track_ids[index_track_id]
        track_destination_id = track_ids[index_track_id+1]


        current_transition_qs = Transition.objects.filter(track_source_id=track_source_id,
                                                       track_destination_id=track_destination_id)
        if not current_transition_qs:
            current_transition = create_transition(track_source_id,
                                       track_destination_id,
                                       PLAYLIST_TRANSITION_AUTO_GENERATED + current_playlist.name)
            if current_transition:  # Seulement ajouter si la transition a été créée avec succès
                logger.info('Generated auto transition :  %s', current_transition)
                transitions.append(current_transition)
            else:
                logger.info(f'Impossible de créer la transition: track {track_source_id} -> {track_destination_id}')
        else:
            current_transition = current_transition_qs[0]
            transitions.append(current_transition)

    return transitions


def get_ordered_tracks_from_playlist(current_playlist: Playlist):
    if not current_playlist:
        return []
    return current_playlist.get_ordered_tracks()


def get_track_ids_from_playlist(current_playlist: Playlist):
    """IDs ordonnés de la playlist. L'existence des tracks est garantie par la FK
    (suppression en cascade), plus besoin de filtrer."""
    if not current_playlist:
        return []
    return current_playlist.get_ordered_track_ids()


def get_order_rank(playlist_name:str) -> int:

    if playlist_name.startswith('2030'):
        return 100
    elif playlist_name.startswith('2029'):
        return 110
    elif playlist_name.startswith('2028'):
        return 120
    elif playlist_name.startswith('2027'):
        return 130
    elif playlist_name.startswith('2027'):
        return 140
    elif playlist_name.startswith('2026'):
        return 150
    elif playlist_name.startswith('2025'):
        return 160
    elif playlist_name.startswith('2024'):
        return 170
    elif playlist_name.startswith('2023'):
        return 180
    elif playlist_name.startswith('2022'):
        return 185
    elif playlist_name.startswith('2021'):
        return 190
    elif playlist_name.startswith('2020'):
        return 195
    elif playlist_name.startswith('2021'):
        return 196

    if is_name_parsable_for_numeric_indexing(playlist_name):
        return 999

    return string.ascii_lowercase.index(playlist_name[0].lower()) + 200


def is_name_parsable_for_numeric_indexing(playlist_name):
    return (not playlist_name
            or len(playlist_name) == 0
            or playlist_name[0] == ''
            or not playlist_name[0].lower()
            or not playlist_name[0].isalpha())


def delete_playlist_transitions(request):
    logger.info('DELETE playlist transitions....')
    playlist_id = request.GET['playlistId']
    all_playlist_transitions = get_transitions_from_playlist(Playlist.objects.get(id=playlist_id))
    deleted = 0
    for current_transition in all_playlist_transitions:
        if PLAYLIST_TRANSITION_AUTO_GENERATED in current_transition.comment:
            current_transition.delete()
            deleted += 1
            logger.info('Transition DELETED  %s / %s', current_transition.track_source.title, current_transition.track_destination.title)
    # Pas de rafraîchissement de page: réafficher la playlist regénérerait ces transitions
    return JsonResponse({'success': True, 'deleted': deleted})


def delete_all_generated_transitions(request):
    logger.info('DELETE ALL generated transitions....')
    all_generated_transitions = Transition.objects.filter(comment__contains=PLAYLIST_TRANSITION_AUTO_GENERATED)
    deleted, _ = all_generated_transitions.delete()
    return JsonResponse({'success': True, 'deleted': deleted})


def get_playlists_by_track_id(track_id: int) -> list:
    playlists = Playlist.objects.filter(tracks__id=track_id).distinct()
    # Order in Python using existing get_order_rank to avoid duplicated ranking logic
    # Si même rank, trier par ID décroissant
    ordered = sorted(playlists, key=lambda p: (get_order_rank(p.name), -p.id))
    return ordered
