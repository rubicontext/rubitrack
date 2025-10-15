import datetime
import xml.dom.minidom
import pytz
from xml.dom.minicompat import NodeList
from xml.dom.minidom import Element

from django import forms
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from ..models import Playlist, Track, Artist, Genre, Collection, CuePoint, TrackCuePoints
from ..musical_key.utils import (
    extract_musical_key_from_filename,
    get_conflicting_musical_keys,  # kept for compatibility if used elsewhere
    normalize_musical_key_notation,
)
from ..playlist.playlist_transitions import get_order_rank

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
    user_collection = get_default_collection_for_user(user)

    new_tracks = 0
    existing_tracks = 0
    for current_entry in entry_list:
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
        genre_name = get_genre_from_info(info)
        comment = get_comment_from_info(info)
        comment2 = get_rating_from_info(info)
        playcount = get_playcount_from_info(info)
        last_played_date = get_last_played_date_from_info(info)
        musical_key = get_musical_key_from_info(info)
        bitrate = get_bit_rate_from_info(info)
        bpm = get_bpm_from_info(current_entry)
        ranking = get_ranking_from_xml_info(info)
        genre = get_genre_db_from_genre_name(genre_name)

        track_list = Track.objects.filter(title=title, artist=artist)
        if track_list:
            track = track_list[0]
            existing_tracks += 1
        else:
            track_list = Track.objects.filter(audio_id=audio_id)
            if track_list:
                track = track_list[0]
                track.title = title
                existing_tracks += 1
            else:
                track = Track(title=title)
                new_tracks += 1

        track.artist = artist
        track.genre = genre
        track.comment = comment
        track.comment2 = comment2
        track.ranking = ranking
        track.playcount = playcount
        track.date_last_played = last_played_date

        determined_key = normalize_musical_key_notation(musical_key) if musical_key else extract_musical_key_from_filename(file_name)
        track.musical_key = determined_key

        if determined_key:
            if determined_key != musical_key:
                print(f"🔄 Clé musicale pour '{title}': {musical_key} → {determined_key}")
        else:
            if musical_key:
                print(f"⚠️  Impossible de normaliser la clé pour '{title}': {musical_key}")

        track.bitrate = bitrate
        track.bpm = bpm
        track.audio_id = audio_id
        track.file_name = file_name
        track.location_dir = location_dir
        track.file_path = file_path
        track.save()

        add_track_to_user_collection(user_collection, track)
        extract_and_save_cue_points(current_entry, track)

    import_playlist_from_xml_doc(xmldoc)
    return new_tracks, existing_tracks


# --- XML extract helpers (kept same for clarity) ---

def get_title_from_entry(current_entry):
    return current_entry.attributes['TITLE'].value


def get_audio_id_from_entry(current_entry):
    if 'AUDIO_ID' in current_entry.attributes:
        return current_entry.attributes['AUDIO_ID'].value
    print('WARNING no audio_id tag for entry : ', get_title_from_entry(current_entry))
    return None


def get_artist_from_entry(current_entry):
    artist_name = get_artist_name_from_entry(current_entry)
    return get_artist_db_from_artist_name(artist_name)


def get_artist_name_from_entry(current_entry):
    return current_entry.attributes['ARTIST'].value if 'ARTIST' in current_entry.attributes else UNKNOWN_ARTIST_NAME


def get_bpm_from_info(current_entry):
    tempo = current_entry.getElementsByTagName('TEMPO')
    if tempo and ('BPM' in tempo[0].attributes):
        return tempo[0].attributes['BPM'].value
    return None


def get_bit_rate_from_info(info):
    return info[0].attributes['BITRATE'].value if 'BITRATE' in info[0].attributes else 0


def get_musical_key_from_info(info):
    if 'KEY' in info[0].attributes:
        key = info[0].attributes['KEY'].value
        if len(key) > MAX_MUSICAL_KEY_LENGTH:
            key = key[:MAX_MUSICAL_KEY_LENGTH]
        return key
    return 0


def get_last_played_date_from_info(info):
    if 'LAST_PLAYED' in info[0].attributes:
        last_played_date_str = info[0].attributes['LAST_PLAYED'].value
        last_played_date = datetime.datetime.strptime(last_played_date_str, '%Y/%m/%d')
        return last_played_date.replace(tzinfo=pytz.UTC)
    return None


def get_playcount_from_info(info):
    return info[0].attributes['PLAYCOUNT'].value if 'PLAYCOUNT' in info[0].attributes else 0


def get_rating_from_info(info):
    return info[0].attributes['RATING'].value if 'RATING' in info[0].attributes else ''


def get_comment_from_info(info):
    if 'COMMENT' in info[0].attributes:
        comment = info[0].attributes['COMMENT'].value
        return comment[:MAX_COMMENT_LENGTH]
    return ''


def get_genre_from_info(info):
    if 'GENRE' in info[0].attributes:
        genre_name = info[0].attributes['GENRE'].value
        return genre_name[:MAX_GENRE_LENGTH]
    return None


def get_artist_db_from_artist_name(artist_name):
    try:
        return Artist.objects.get(name=artist_name)
    except Artist.DoesNotExist:
        artist = Artist(name=artist_name)
        artist.save()
        return artist


def get_genre_db_from_genre_name(genre_name):
    if genre_name is None:
        return None
    try:
        return Genre.objects.get(name=genre_name)
    except Genre.DoesNotExist:
        genre = Genre(name=genre_name)
        genre.save()
        return genre


@login_required
def upload_file(request):
    if request.method == 'POST':
        form = UploadCollectionForm(request.POST, request.FILES)
        if form.is_valid():
            current_user = request.user
            new_tracks, existing_tracks = handle_uploaded_file(request.FILES['file'], current_user)
            return render(
                request,
                'track/collection/import_collection.html',
                {
                    'form': form,
                    'nb_new_tracks': new_tracks,
                    'nb_existing_tracks': existing_tracks,
                    'submitted': True,
                },
            )
    else:
        form = UploadCollectionForm()
    return render(request, 'track/collection/import_collection.html', {'form': form})


def get_default_collection_for_user(current_user):
    collection_list = Collection.objects.filter(user=current_user)
    if not collection_list:
        collection = Collection(user=current_user, name='User collection')
        collection.save()
    else:
        collection = collection_list[0]
    return collection


def add_track_to_user_collection(collection: Collection, track: Track) -> bool:
    existing_track = collection.tracks.filter(title=track.title, artist=track.artist)
    if existing_track is None:
        collection.tracks.append(track)
        return True
    return False


def get_ranking_from_xml_info(info) -> int:
    if 'RANKING' not in info[0].attributes:
        return 0
    try:
        ranking_int = int(info[0].attributes['RANKING'].value)
    except (ValueError, TypeError):
        return 0
    if ranking_int == 255:
        return 5
    if ranking_int == 204:
        return 4
    if ranking_int == 153:
        return 3
    if ranking_int == 99:
        return 2
    if ranking_int == 51:
        return 1
    return 0


def extract_and_save_cue_points(current_entry, track):
    cue_points_list = current_entry.getElementsByTagName('CUE_V2')
    if not cue_points_list:
        print(f"No cue points found for track: {track.title}")
        return
    track_cue_points, _ = TrackCuePoints.objects.get_or_create(track=track)
    for i in range(1, 9):
        old_cue_point = getattr(track_cue_points, f'cue_point_{i}')
        if old_cue_point:
            old_cue_point.delete()
        setattr(track_cue_points, f'cue_point_{i}', None)
    cue_point_count = 0
    for cue_point_xml in cue_points_list:
        if cue_point_count >= 8:
            break
        if 'START' not in cue_point_xml.attributes:
            continue
        start_ms = cue_point_xml.attributes['START'].value
        try:
            total_seconds = int(float(start_ms)) // 1000
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            time_formatted = f"{minutes}:{seconds:02d}"
        except (ValueError, TypeError):
            print(f"Invalid START time for cue point: {start_ms}")
            continue
        cue_type = cue_point_xml.attributes['NAME'].value if 'NAME' in cue_point_xml.attributes else ""
        cue_comment = cue_type
        if 'TYPE' in cue_point_xml.attributes:
            type_value = cue_point_xml.attributes['TYPE'].value
            if cue_comment and type_value != cue_type:
                cue_comment += f" (Type: {type_value})"
            elif not cue_comment:
                cue_comment = f"Type: {type_value}"
        if 'HOTCUE' in cue_point_xml.attributes:
            hotcue = cue_point_xml.attributes['HOTCUE'].value
            if hotcue != "0":
                cue_comment += f" [Hotcue {hotcue}]"
        cue_point = CuePoint.objects.create(time=time_formatted, type=cue_type, comment=cue_comment)
        cue_point_count += 1
        setattr(track_cue_points, f'cue_point_{cue_point_count}', cue_point)
        print(f"Created cue point {cue_point_count} for {track.title}: {time_formatted} ({cue_type})")
    track_cue_points.save()
    print(f"Saved {cue_point_count} cue points for track: {track.title}")


def convert_milliseconds_to_time_format(milliseconds_str):
    try:
        total_seconds = int(float(milliseconds_str)) // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:02d}"
    except (ValueError, TypeError):
        return "0:00"


def import_playlist_from_xml_doc(xmldoc):
    playlists = xmldoc.getElementsByTagName('PLAYLISTS')
    playlist_list = playlists[0].getElementsByTagName('NODE')
    existing_playlist_count = 0
    new_playlist_count = 0
    # counters below kept for potential future metrics
    for current_playlist in playlist_list:
        node_type = current_playlist.attributes['TYPE'].value
        if node_type != 'PLAYLIST':
            continue
        name = current_playlist.attributes['NAME'].value
        playlist = get_or_create_single_playlist_from_name(existing_playlist_count, new_playlist_count, name)
        playlist_entry_list = current_playlist.getElementsByTagName('ENTRY')
        if len(playlist_entry_list) == len(playlist.tracks.all()):
            continue
        track_ids = []
        for current_entry in playlist_entry_list:
            for key in current_entry.getElementsByTagName('PRIMARYKEY'):
                file_path = key.attributes['KEY'].value
                track_list = Track.objects.filter(file_path=file_path)
                if not track_list:
                    print('WARNING - Track not found for file_path: ', file_path)
                    continue
                track = track_list[0]
                track_ids.append(track.id)
                playlist.tracks.add(track)
        print('Playlist tracks ids: ', track_ids)
        playlist.track_ids = track_ids
        playlist.save()


def get_or_create_single_playlist_from_name(existing_playlist_count: int, new_playlist_count: int, name: str) -> Playlist:
    print('PLAYLIST NAME: ', name)
    existing_playlists = Playlist.objects.filter(name=name)
    if existing_playlists:
        playlist = existing_playlists[0]
        playlist.save()
        existing_playlist_count += 1
    else:
        playlist = Playlist(name=name, rank=get_order_rank(name))
        playlist.save()
        new_playlist_count += 1
    return playlist