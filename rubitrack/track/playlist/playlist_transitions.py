import ast

import string

from django.shortcuts import render

from django.contrib.auth.decorators import login_required

from track.currently_playing.transition import create_transition

from ..models import Track, Transition, Playlist

PLAYLIST_TRANSITION_AUTO_GENERATED = 'Generated from Playlist : '
SEPARATOR_TRACK_ID = 14294

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
        print("All transitions for playlist : ", currentPlaylist)
        return render(
            request,
            'track/playlists/playlist_transitions.html',
            {
                'currentPlaylist': currentPlaylist,
                'playlistTransitions': playlistTransitions,
                'playlistTracks': playlistTracks,
                'firstTrack': playlistTracks[0],
            },
        )
    

def get_transitions_from_playlist(current_playlist: Playlist):
    if not current_playlist or not current_playlist.track_ids or len(current_playlist.track_ids) < 2:
        return []

    transitions = []
    track_ids = get_track_ids_from_playlist(current_playlist)
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
                print('Generated auto transition : ', current_transition)
                transitions.append(current_transition)
            else:
                print(f'Impossible de créer la transition: track {track_source_id} -> {track_destination_id}')
        else:
            current_transition = current_transition_qs[0]
            transitions.append(current_transition)

    return transitions


def get_ordered_tracks_from_playlist(current_playlist: Playlist):
    if not current_playlist or not current_playlist.track_ids:
        return []

    ordered_tracks = []
    for track_id in get_track_ids_from_playlist(current_playlist):
        current_track = Track.objects.get(id=track_id)
        if current_track:
            ordered_tracks.append(current_track)

    return ordered_tracks


def get_track_ids_from_playlist(current_playlist: Playlist):
    if not current_playlist or not current_playlist.track_ids:
        return []
    
    # Parser les IDs depuis la chaîne stockée
    all_track_ids = ast.literal_eval(current_playlist.track_ids)
    
    # Filtrer pour ne garder que les tracks qui existent encore
    existing_track_ids = []
    for track_id in all_track_ids:
        if Track.objects.filter(id=track_id).exists():
            existing_track_ids.append(track_id)
        else:
            print(f"Track avec ID {track_id} n'existe plus, ignoré dans la playlist {current_playlist.name}")
    
    return existing_track_ids


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
    elif playlist_name.startswith('2025'):
        return 150
    elif playlist_name.startswith('2024'):
        return 160
    elif playlist_name.startswith('2023'):
        return 170
    elif playlist_name.startswith('2022'):
        return 180
    elif playlist_name.startswith('2021'):
        return 185
    elif playlist_name.startswith('2020'):
        return 190
    elif playlist_name.startswith('2019'):
        return 195
    
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
    print('DELETE playlist transitions....')
    playlistId = request.GET['playlistId']
    all_playlist_transitions = get_transitions_from_playlist(Playlist.objects.get(id=playlistId))
    for current_transition in all_playlist_transitions:
        print('COMMENT : ', current_transition.comment)
        if PLAYLIST_TRANSITION_AUTO_GENERATED in current_transition.comment:
            current_transition.delete()
            print('Transition DELETED ', current_transition.track_source.title, '/', current_transition.track_destination.title)

    #TODO a date on ne renvoit rien, page non mise à jour car sinon on va re générer ces transitions..
    return None


def delete_all_generated_transitions(request):
    print('DELETE ALL generated transitions....')
    all_genrated_transitions = Transition.objects.filter(comment__contains=PLAYLIST_TRANSITION_AUTO_GENERATED)
    all_genrated_transitions.delete()
    return None


def get_playlists_by_track_id(track_id: int) -> list:
    playlists = Playlist.objects.filter(tracks__id=track_id).distinct()
    # Order in Python using existing get_order_rank to avoid duplicated ranking logic
    ordered = sorted(playlists, key=lambda p: (get_order_rank(p.name), p.name.lower() if p.name else ''))
    return ordered