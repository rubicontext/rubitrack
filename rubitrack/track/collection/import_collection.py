import datetime
from xml.dom.minicompat import NodeList
from xml.dom.minidom import Element
import pytz

from django import forms
from django.shortcuts import render

from track.playlist.playlist_transitions import get_order_rank
from ..models import Playlist, Track, Artist, Genre, Collection

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
    userCollection = get_default_collection_for_user(user)

    cptNewTracks = 0
    cptExistingTracks = 0
    for current_entry in entry_list:
        # for current_entry in entry_list[0:10]:

        # sample auto imported must be ignored
        info = current_entry.getElementsByTagName('INFO')
        if not info:
            continue

        title = get_title_from_entry(current_entry)
        audio_id = get_audio_id_from_entry(current_entry)
        location = current_entry.getElementsByTagName('LOCATION')
        file_name = location[0].attributes['FILE'].value
        location_dir = location[0].attributes['VOLUME'].value + location[0].attributes['DIR'].value
        file_path = location_dir + file_name


        artist = get_artist_from_entry(current_entry)
        genreName = get_genre_from_info(info)
        comment = get_comment_from_info(info)
        comment2 = get_rating_from_info(info)
        playcount = get_playcount_from_info(info)
        lastPlayedDate = get_last_played_date_from_info(info)
        musicalKey = get_musical_key_from_info(info)
        bitrate = get_bit_rate_from_info(info)
        bpm = get_bpm_from_info(current_entry)
        ranking = get_ranking_from_xml_info(info)
        genre = get_genre_db_from_genre_name(genreName)

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

    import_playlist_from_xml_doc(xmldoc)

    return cptNewTracks, cptExistingTracks


def get_title_from_entry(current_entry):
    return current_entry.attributes['TITLE'].value


def get_audio_id_from_entry(current_entry):
    if 'AUDIO_ID' in current_entry.attributes:
        return current_entry.attributes['AUDIO_ID'].value
    else:
        print('WARNING no audio_id tag for entry : ', get_title_from_entry(current_entry))
        return None


def get_artist_from_entry(current_entry):
    artistName = get_artist_name_from_entry(current_entry)
    artist = get_artist_db_from_artist_name(artistName)
    return artist


def get_artist_name_from_entry(current_entry):
    if 'ARTIST' in current_entry.attributes:
        artistName = current_entry.attributes['ARTIST'].value
    else:
        artistName = UNKNOWN_ARTIST_NAME
    return artistName


def get_bpm_from_info(current_entry):
    tempo = current_entry.getElementsByTagName('TEMPO')
    if len(tempo) > 0 and ('BPM' in tempo[0].attributes):
        bpm = tempo[0].attributes['BPM'].value
    else:
        bpm = None
    return bpm


def get_bit_rate_from_info(info):
    if 'BITRATE' in info[0].attributes:
        bitrate = info[0].attributes['BITRATE'].value
    else:
        bitrate = 0
    return bitrate


def get_musical_key_from_info(info):
    if 'KEY' in info[0].attributes:
        musicalKey = info[0].attributes['KEY'].value
        if len(musicalKey) > MAX_MUSICAL_KEY_LENGTH:
            musicalKey = musicalKey[0:MAX_MUSICAL_KEY_LENGTH]
    else:
        musicalKey = 0
    return musicalKey


def get_last_played_date_from_info(info):
    if 'LAST_PLAYED' in info[0].attributes:
        lastPlayedDateStr = info[0].attributes['LAST_PLAYED'].value
        lastPlayedDate = datetime.datetime.strptime(lastPlayedDateStr, '%Y/%m/%d')
        lastPlayedDate = lastPlayedDate.replace(tzinfo=pytz.UTC)
    else:
        lastPlayedDate = None
    return lastPlayedDate


def get_playcount_from_info(info):
    if 'PLAYCOUNT' in info[0].attributes:
        playcount = info[0].attributes['PLAYCOUNT'].value
    else:
        playcount = 0
    return playcount


def get_rating_from_info(info):
    if 'RATING' in info[0].attributes:
        comment2 = info[0].attributes['RATING'].value
    else:
        comment2 = ''
    return comment2


def get_comment_from_info(info):
    if 'COMMENT' in info[0].attributes:
        comment = info[0].attributes['COMMENT'].value
        if len(comment) > MAX_COMMENT_LENGTH:
            comment = comment[0:MAX_COMMENT_LENGTH]
    else:
        comment = ''
    return comment


def get_genre_from_info(info):
    if 'GENRE' in info[0].attributes:
        genreName = info[0].attributes['GENRE'].value
        if len(genreName) > MAX_GENRE_LENGTH:
            genreName = genreName[0:MAX_GENRE_LENGTH]
    else:
        genreName = None
    return genreName


def get_artist_db_from_artist_name(artistName):
    try:
        ArtistDb = Artist.objects.get(name=artistName)
        artist = ArtistDb
    except Artist.DoesNotExist:
        artist = Artist()
        artist.name = artistName
        artist.save()

    return artist


def get_genre_db_from_genre_name(genreName):
    if genreName is not None:
        try:
            GenreDb = Genre.objects.get(name=genreName)
            genre = GenreDb
        except Genre.DoesNotExist:
            genre = Genre()
            genre.name = genreName
            genre.save()
    else:
        genre = None

    return genre


@login_required
def upload_file(request):
    if request.method == 'POST':
        form = UploadCollectionForm(request.POST, request.FILES)
        if form.is_valid():
            current_user = request.user
            cptNewTracks, cptExistingTracks = handle_uploaded_file(request.FILES['file'], current_user)
            return render(
                request,
                'track/collection/import_collection.html',
                {
                    'form': form,
                    'nb_new_tracks': cptNewTracks,
                    'nb_existing_tracks': cptExistingTracks,
                    'submitted': True,
                },
            )
    else:
        form = UploadCollectionForm()
    return render(request, 'track/collection/import_collection.html', {'form': form})


def get_default_collection_for_user(currentUser):
    collectionList = Collection.objects.filter(user=currentUser)
    if len(collectionList) < 1:
        collection = Collection()
        collection.user = currentUser
        collection.name = 'User collection'
        collection.save()
    else:
        collection = collectionList[0]
    return collection


def add_track_to_user_collection(collection: Collection, track: Track) -> bool:
    existingTrack = collection.tracks.filter(title=track.title, artist=track.artist)
    if existingTrack is None:
        collection.tracks.append(track)
        return True
    return False


def get_ranking_from_xml_info(info) -> int:
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


def import_playlist_from_xml_doc(xmldoc):

    playlists = xmldoc.getElementsByTagName('PLAYLISTS')
    playlist_list = playlists[0].getElementsByTagName('NODE')

    existing_playlist_count = 0
    new_playlist_count = 0
    track_found_count = 0
    track_not_found_count = 0

    # for current_playlist in playlist_list[0:10]:
    for current_playlist in playlist_list:

        # NODE TYPE
        node_type = current_playlist.attributes['TYPE'].value
        if node_type != 'PLAYLIST':
            continue

        # PLAYLIST NAME
        name = current_playlist.attributes['NAME'].value
        playlist = get_or_create_single_playlist_from_name(existing_playlist_count, new_playlist_count, name)

        # PLAYLIST TRACKS
        playlist_entry_list = current_playlist.getElementsByTagName('ENTRY')
        track_ids = []

        # option 1 we reset all tracks to avoid deletion undetected (could be improved?)
        # playlist.tracks.clear()

        # option 2, we check if number of track has changed (DANGEROUS!)
        if len(playlist_entry_list) == len(playlist.tracks.all()):
            continue

        # option 3, we check for equality in track ids list and order?

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
                playlist.tracks.add(track)

        print('Playlist tracks ids: ', track_ids)
        playlist.track_ids = track_ids
        playlist.save()


def get_or_create_single_playlist_from_name(
    existing_playlist_count: int, new_playlist_count: int, name: str
) -> Playlist:
    print('PLAYLIST NAME: ', name)
    existing_playlists = Playlist.objects.filter(name=name)
    if len(existing_playlists) > 0:
        playlist = existing_playlists[0]
        playlist.save()
        existing_playlist_count = existing_playlist_count + 1
    else:
        playlist = Playlist()
        playlist.name = name
        playlist.rank = get_order_rank(name)
        new_playlist_count = new_playlist_count + 1
        playlist.save()
    return playlist
