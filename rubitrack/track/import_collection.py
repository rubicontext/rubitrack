
import datetime
import json
import pytz

from django import forms
from django.shortcuts import render
from .models import Playlist, Track, Artist, Genre, Collection

from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required

import xml.dom.minidom

UNKNOWN_ARTIST_NAME = "Unknown Artist"
MAX_COMMENT_LENGTH = 500
MAX_MUSICAL_KEY_LENGTH = 3
MAX_GENRE_LENGTH = 3


class UploadCollectionForm(forms.Form):
    file = forms.FileField()


def handle_uploaded_file(file, user):

    xmldoc = xml.dom.minidom.parse(file)
    collection = xmldoc.getElementsByTagName('COLLECTION')
    entry_list = collection[0].getElementsByTagName('ENTRY')
    # key_list = entry_list[0].getElementsByTagName('KEY')

    # get or init a collection object for this user
    userCollection = get_default_collection_for_user(user)

    cptNewTracks = 0
    cptExistingTracks = 0
    # for current_entry in entry_list :
    for current_entry in entry_list[0:10]:
        # print(current_entry.attributes)
        title = current_entry.attributes['TITLE'].value

        # audio ID
        if 'AUDIO_ID' in current_entry.attributes:
            audio_id = current_entry.attributes['AUDIO_ID'].value
        else:
            audio_id = None
            print('WARNING no audio_id tag for entry : ', title)

        if 'ARTIST' in current_entry.attributes:
            artistName = current_entry.attributes['ARTIST'].value
        else:
            artistName = UNKNOWN_ARTIST_NAME

        location = current_entry.getElementsByTagName('LOCATION')
        file_name = location[0].attributes['FILE'].value
        location_dir = location[0].attributes['VOLUME'].value + location[0].attributes['DIR'].value
        file_path = location_dir + file_name
        # print("FILE: ", file_name, " DIR: ", location_dir)

        # sample auto imported must be ignored
        info = current_entry.getElementsByTagName('INFO')
        if not info:
            continue

        # genre
        if 'GENRE' in info[0].attributes:
            genreName = info[0].attributes['GENRE'].value
            if len(genreName) > MAX_GENRE_LENGTH:
                genreName = genreName[0:MAX_GENRE_LENGTH]
        else:
            genreName = None

        # comment
        if 'COMMENT' in info[0].attributes:
            comment = info[0].attributes['COMMENT'].value
            if len(comment) > MAX_COMMENT_LENGTH:
                comment = comment[0:MAX_COMMENT_LENGTH]
        else:
            comment = ''

        if 'RATING' in info[0].attributes:
            comment2 = info[0].attributes['RATING'].value
        else:
            comment2 = ''

        if 'PLAYCOUNT' in info[0].attributes:
            playcount = info[0].attributes['PLAYCOUNT'].value
        else:
            playcount = 0

        if 'LAST_PLAYED' in info[0].attributes:
            lastPlayedDateStr = info[0].attributes['LAST_PLAYED'].value
            lastPlayedDate = datetime.datetime.strptime(lastPlayedDateStr, '%Y/%m/%d')
            lastPlayedDate = lastPlayedDate.replace(tzinfo=pytz.UTC)
        else:
            lastPlayedDate = None

        if 'IMPORT_DATE' in info[0].attributes:
            importDateStr = info[0].attributes['IMPORT_DATE'].value
            importDate = datetime.datetime.strptime(importDateStr, '%Y/%m/%d').strftime('%Y-%m-%d')
        else:
            importDate = None

        # musicalKey
        if 'KEY' in info[0].attributes:
            musicalKey = info[0].attributes['KEY'].value
            if len(musicalKey) > MAX_MUSICAL_KEY_LENGTH:
                musicalKey = musicalKey[0:MAX_MUSICAL_KEY_LENGTH]
        else:
            musicalKey = 0

        if 'BITRATE' in info[0].attributes:
            bitrate = info[0].attributes['BITRATE'].value
        else:
            bitrate = 0

        tempo = current_entry.getElementsByTagName('TEMPO')
        if len(tempo) > 0 and ('BPM' in tempo[0].attributes):
            bpm = tempo[0].attributes['BPM'].value
        else:
            bpm = None

        ranking = get_ranking_from_xml_info(info)

        # check if ARTIST exists, or insert it
        try:
            ArtistDb = Artist.objects.get(name=artistName)
            artist = ArtistDb
        except Artist.DoesNotExist:
            artist = Artist()
            artist.name = artistName
            artist.save()

        # check if GENRE exists, or insert it
        if genreName is not None:
            try:
                GenreDb = Genre.objects.get(name=genreName)
                genre = GenreDb
                # print("Found existing genre : ", genreName)
            except Genre.DoesNotExist:
                genre = Genre()
                genre.name = genreName
                genre.save()
                # print("Created new genre : ", genreName)
        else:
            genre = None

        # Check if TRACK exists or insert it
        # trackDb = Track.objects.get(title=title, artist=artist)
        # 1 find by artist and title
        trackList = Track.objects.filter(title=title, artist=artist)
        if len(trackList) > 0:
            trackDb = trackList[0]
            track = trackDb
            cptExistingTracks = cptExistingTracks + 1
        else:
            # 2 find by audio ID
            trackList = Track.objects.filter(audio_id=audio_id)
            if len(trackList) > 0:
                trackDb = trackList[0]
                track = trackDb
                track.title = title
                cptExistingTracks = cptExistingTracks + 1
            # 3 create it!
            else:
                track = Track()
                track.title = title
                cptNewTracks = cptNewTracks + 1

        # update track infos
        track.artist = artist
        track.genre = genre
        track.comment = comment
        track.comment2 = comment2
        track.ranking = ranking
        track.playcount = playcount
        track.date_last_played = lastPlayedDate
        track.musical_key = musicalKey
        track.bitrate = bitrate
        track.bpm = bpm
        track.audio_id = audio_id
        track.file_name = file_name
        track.location_dir = location_dir
        track.file_path = file_path

        track.save()
        add_track_to_user_collection(userCollection, track)

    import_playlist_from_xml_doc(xmldoc, user)

    # print('xml parsing DONE!')
    return cptNewTracks, cptExistingTracks

    # traverseTree(xml.documentElement)


@login_required
def upload_file(request):
    if request.method == 'POST':
        form = UploadCollectionForm(request.POST, request.FILES)
        if form.is_valid():
            # print('Form is valid!')
            # get user
            current_user = request.user
            # print current_user.id
            cptNewTracks, cptExistingTracks = handle_uploaded_file(request.FILES['file'], current_user)
            # return HttpResponseRedirect('/admin/')
            return render(
                request,
                'track/import_collection.html',
                {
                    'form': form,
                    'nb_new_tracks': cptNewTracks,
                    'nb_existing_tracks': cptExistingTracks,
                    'submitted': True,
                },
            )
    else:
        form = UploadCollectionForm()
    return render(request, 'track/import_collection.html', {'form': form})


def get_default_collection_for_user(currentUser):
    collectionList = Collection.objects.filter(user=currentUser)
    if len(collectionList) < 1:
        # create new collection
        collection = Collection()
        collection.user = currentUser
        collection.name = 'User collection'
        collection.save()
    else:
        collection = collectionList[0]
    return collection


def add_track_to_user_collection(collection, track):
    existingTrack = collection.tracks.filter(title=track.title, artist=track.artist)
    if existingTrack is None:
        collection.tracks.append(track)
        return True
    return False


def get_ranking_from_xml_info(info):
    """convert ranking from traktor (0-255) to regular 1-5 star system"""
    if 'RANKING' not in info[0].attributes:
        return None
    rankingTraktor = info[0].attributes['RANKING'].value
    if rankingTraktor == 255:
        ranking = 5
    elif rankingTraktor == 204:
        ranking = 4
    elif rankingTraktor == 153:
        ranking = 3
    elif rankingTraktor == 99:
        ranking = 2
    elif rankingTraktor == 51:
        ranking = 1
    else:
        ranking = 0
    return ranking


def import_playlist_from_xml_doc(xmldoc, user):

    playlists = xmldoc.getElementsByTagName('PLAYLISTS')
    playlist_list = playlists[0].getElementsByTagName('NODE')

    existing_playlist_count = 0
    new_playlist_count = 0
    track_found_count = 0
    track_not_found_count = 0

    for current_playlist in playlist_list[0:10]:
    # for current_playlist in playlist_list:

        # NODE TYPE
        node_type = current_playlist.attributes['TYPE'].value
        if node_type != 'PLAYLIST':
            continue

        # PLAYLIST NAME
        name = current_playlist.attributes['NAME'].value
        print('PLAYLIST NAME: ', name)
        existing_playlists = Playlist.objects.filter(name=name)
        if len(existing_playlists) > 0:
            playlist = existing_playlists[0]
            existing_playlist_count = existing_playlist_count + 1
        else:
            playlist = Playlist()
            playlist.name = name
            new_playlist_count = new_playlist_count + 1
            playlist.save()

        # PLAYLIST TRACKS
        playlist_entry_list = current_playlist.getElementsByTagName('ENTRY')
        track_ids = []
        for current_entry in playlist_entry_list:
            for key in current_entry.getElementsByTagName('PRIMARYKEY'):
                file_path = key.attributes['KEY'].value

                trackList = Track.objects.filter(file_path=file_path)
                if len(trackList) == 0:
                    track_not_found_count = track_not_found_count + 1
                    print('WARNING - Track not found for file_path: ', file_path)
                    continue

                track = trackList[0]
                track_found_count = track_found_count + 1
                track_ids.append(track.id)
                if track not in playlist.tracks.all():
                    playlist.tracks.add(track)

            playlist.track_ids = json.dumps(track_ids)
            # to read back the list of track ids
            jsonDec = json.decoder.JSONDecoder()
            print('Playlist tracks ids: ', jsonDec.decode(playlist.track_ids))
            playlist.save()
