import ast

import string

from django.shortcuts import render

from django.contrib.auth.decorators import login_required

from track.transition import create_transition

from ..models import Track, Transition, Playlist

PLAYLIST_TRANSITION_AUTO_GENERATED = 'Generated from Playlist : '

@login_required
def display_playlist_transitions(request, PlaylistId):
    currentPlaylist = Playlist.objects.get(id=PlaylistId)
    if currentPlaylist is None:
        return render(
            request,
            'track/playlist_transitions.html',
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
            'track/playlist_transitions.html',
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
        current_transition: Transition = Transition.objects.filter(track_source_id=track_source_id,
                                                       track_destination_id=track_destination_id)
        if not current_transition:
            # TODO risqué d'avoir de nombreuses transitions 'Bidon', on verra a l'usage...
            current_transition: Transition = create_transition(track_source_id, 
                                                   track_destination_id,
                                                   PLAYLIST_TRANSITION_AUTO_GENERATED + current_playlist.name)
            print('Generated auto transition : ', current_transition)
        else:
            #TODO attention si multiples transitions pour 2 tracks, pas géré
            current_transition = current_transition[0]
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

    return ast.literal_eval(current_playlist.track_ids)


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
    
    if (not playlist_name
        or len(playlist_name) == 0
        or playlist_name[0] == ''
        or not playlist_name[0].lower()
        or not playlist_name[0].isalpha()
        ):
        return 999

    return string.ascii_lowercase.index(playlist_name[0].lower()) + 200

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