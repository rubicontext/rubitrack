import datetime
from xml.dom.minicompat import NodeList
from xml.dom.minidom import Element
import pytz
import re
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import Optional, Set

from django import forms
from django.shortcuts import render

from track.playlist.playlist_transitions import get_order_rank
from ..models import Playlist, Track, Artist, Genre, Collection, CuePoint, TrackCuePoints
from ..musical_key.musical_key_utils import extract_musical_key_from_filename, get_conflicting_musical_keys, normalize_musical_key_notation

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
    # Evite les doublons d'ENTRY pour le même morceau (first-wins)
    processed_keys: Set[str] = set()
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

        # Clé de dédoublonnage: priorité à AudioId, sinon chemin, sinon couple artist+title
        artist_name_key = get_artist_name_from_entry(current_entry)
        if audio_id:
            dedup_key = f"audio:{audio_id}"
        elif file_path:
            dedup_key = f"path:{file_path.lower()}"
        else:
            dedup_key = f"tt:{artist_name_key.lower()}|{title.lower()}"
        if dedup_key in processed_keys:
            # Duplicate ENTRY for same track → skip to preserve first values
            continue
        processed_keys.add(dedup_key)


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
        
        # Utilisation de la méthode normalize pour déterminer la clé musicale
        # Priorité : champ KEY -> nom de fichier
        determined_key = normalize_musical_key_notation(musicalKey) if musicalKey else extract_musical_key_from_filename(file_name)
        track.musical_key = determined_key
            
        track.bitrate = bitrate
        track.bpm = bpm
        track.audio_id = audio_id
        track.file_name = file_name
        track.location_dir = location_dir
        track.file_path = file_path

        track.save()
        add_track_to_user_collection(userCollection, track)
        
        # Extract and save cue points
        extract_and_save_cue_points(current_entry, track)

    import_playlist_from_xml_doc(xmldoc, userCollection)

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
        return 0  # Retourner 0 au lieu de None
    rankingTraktor = info[0].attributes['RANKING'].value
    
    # Convertir en entier pour comparaison
    try:
        ranking_int = int(rankingTraktor)
    except (ValueError, TypeError):
        return 0
        
    if ranking_int == 255:
        ranking = 5
    elif ranking_int == 204:
        ranking = 4
    elif ranking_int == 153:
        ranking = 3
    elif ranking_int == 99:
        ranking = 2
    elif ranking_int == 51:
        ranking = 1
    else:
        ranking = 0
    return ranking


def extract_and_save_cue_points(current_entry, track):
    """
    Extract cue points from XML entry and save them to TrackCuePoints.
    - Map Traktor HOTCUE 0..7 → cue_point_1..8 (RCue1 = HOTCUE=0)
    - START et LEN sont TOUJOURS en millisecondes (Decimal), sans détection d’unité
    - Inclure TYPE=4 (grid) pour remplir RCue1 quand HOTCUE=0 est un grid
    - En cas de doublons sur le même HOTCUE, on garde le premier rencontré (first-wins)
    """
    cue_points_list = current_entry.getElementsByTagName('CUE_V2')
    if not cue_points_list:
        return
        
    track_cue_points, _ = TrackCuePoints.objects.get_or_create(track=track)
    
    # Reset existing 8 slots
    for idx in range(1, 9):
        cp = getattr(track_cue_points, f'cue_point_{idx}')
        if cp:
            cp.delete()
        setattr(track_cue_points, f'cue_point_{idx}', None)
    
    seen_slots: Set[int] = set()
    
    for cue_xml in cue_points_list:
        if not cue_xml.hasAttribute('HOTCUE'):
            continue
        hotcue_val = cue_xml.getAttribute('HOTCUE')
        if not hotcue_val.isdigit():
            continue
        hotcue_index = int(hotcue_val)
        if hotcue_index < 0 or hotcue_index > 7:
            continue
        slot = hotcue_index + 1
        # Skip duplicate entries for the same slot; keep the first one found
        if slot in seen_slots:
            continue
        seen_slots.add(slot)

        traktor_type = cue_xml.getAttribute('TYPE') if cue_xml.hasAttribute('TYPE') else ''
        
        # START (toujours millisecondes)
        if not cue_xml.hasAttribute('START'):
            continue
        start_raw = cue_xml.getAttribute('START')
        try:
            start_ms_dec = Decimal(start_raw)
            seconds_float = float(start_ms_dec / Decimal('1000'))
            minutes = int(seconds_float // 60)
            seconds_part = seconds_float - (minutes * 60)
            time_formatted = f"{minutes}:{seconds_part:06.3f}"
        except (InvalidOperation, ValueError):
            continue
        
        # NAME
        name = cue_xml.getAttribute('NAME') if cue_xml.hasAttribute('NAME') else ''
        
        # LEN (toujours millisecondes)
        duration_seconds = None
        end_time_formatted = None
        len_ms_dec: Optional[Decimal] = None
        if cue_xml.hasAttribute('LEN'):
            try:
                len_raw = cue_xml.getAttribute('LEN')
                len_ms_dec = Decimal(len_raw)
                len_seconds = float(len_ms_dec / Decimal('1000'))
                if len_seconds > 0:
                    duration_seconds = len_seconds
                    end_seconds_float = seconds_float + len_seconds
                    end_minutes = int(end_seconds_float // 60)
                    end_seconds_part = end_seconds_float - (end_minutes * 60)
                    end_time_formatted = f"{end_minutes}:{end_seconds_part:06.3f}"
            except (InvalidOperation, ValueError):
                len_ms_dec = None
        
        comment = name
        if traktor_type and traktor_type != name:
            comment = f"{comment} (Type: {traktor_type})" if comment else f"Type: {traktor_type}"
        
        cue_point = CuePoint.objects.create(
            time=time_formatted,
            type=name,
            comment=comment,
            traktor_type=traktor_type,
            end_time=end_time_formatted,
            duration=duration_seconds,
            time_ms=start_ms_dec,
            len_ms=len_ms_dec
        )
        
        setattr(track_cue_points, f'cue_point_{slot}', cue_point)
    
    track_cue_points.save()


def convert_milliseconds_to_time_format(milliseconds_str: str) -> str:
    """
    Convert milliseconds string to MM:SS.mmm format using Decimal (ROUND_HALF_UP)
    Preserves millisecond precision (3 decimals).
    """
    try:
        ms = Decimal(str(milliseconds_str))
        if ms < 0:
            ms = Decimal('0')
        seconds = ms / Decimal('1000')
        minutes = int(seconds // Decimal('60'))
        seconds_part = seconds - Decimal(minutes) * Decimal('60')
        # Format with 3 decimals, zero-padded seconds to 6 width including decimal part
        return f"{minutes}:{seconds_part.quantize(Decimal('0.000')):06}"
    except (InvalidOperation, ValueError, TypeError):
        return "0:00.000"


def import_playlist_from_xml_doc(xmldoc: Element, user_collection: Collection) -> None:

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
        playlist = get_or_create_single_playlist_from_name(existing_playlist_count, new_playlist_count, name, user_collection)

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

        playlist.track_ids = track_ids
        playlist.save()


def get_or_create_single_playlist_from_name(
    existing_playlist_count: int, new_playlist_count: int, name: str, user_collection: Collection
) -> Playlist:
    existing_playlists = Playlist.objects.filter(name=name)
    if len(existing_playlists) > 0:
        playlist = existing_playlists[0]
        # Backfill collection if missing
        if getattr(playlist, 'collection_id', None) is None:
            playlist.collection = user_collection
        playlist.save()
        existing_playlist_count = existing_playlist_count + 1
    else:
        playlist = Playlist()
        playlist.name = name
        playlist.rank = get_order_rank(name)
        playlist.collection = user_collection
        new_playlist_count = new_playlist_count + 1
        playlist.save()
    return playlist


class TraktorImporter:
    def extract_and_save_cue_points(self, entry_elem, track_obj) -> None:
        """Parse CUE_V2 from Traktor ENTRY and populate Track.cue_points (cue_point_1..8).
        - Map Traktor HOTCUE 0..7 to RCue 1..8 (index = HOTCUE + 1)
        - TYPE 0 (hot cue) → store start, set traktor_type=0
        - TYPE 5 (loop) → store start & len_ms, traktor_type=5
        - TYPE 4 (grid) → ignore for DB cue points
        Preserve millisecond precision in time_ms/len_ms (Decimal up to 6 places).
        """
        from decimal import Decimal
        cue_points = getattr(track_obj, 'cue_points', None)
        if not cue_points:
            return
        # Reset a working dict for 1..8
        slots: dict[int, dict] = {}
        for cue in entry_elem.findall('CUE_V2'):
            try:
                t_type = int(cue.get('TYPE', '0'))
                hot = int(cue.get('HOTCUE', '-1'))
                # Skip grid
                if t_type == 4:
                    continue
                # Only map valid hotcue slots 0..7
                if hot < 0 or hot > 7:
                    continue
                idx = hot + 1  # Traktor HOTCUE 0 → RCue1
                start_raw = cue.get('START', '0')
                len_raw = cue.get('LEN', '0')
                # Traktor provides seconds; convert to ms Decimal
                start_ms = Decimal(str(start_raw)) * Decimal('1000')
                len_ms = Decimal(str(len_raw)) * Decimal('1000') if len_raw and float(len_raw) > 0 else None
                slots[idx] = {
                    'time_ms': start_ms,
                    'len_ms': len_ms,
                    'traktor_type': t_type,
                }
            except Exception:
                continue
        # Apply into cue_points model fields
        for i in range(1, 9):
            data = slots.get(i)
            if not data:
                continue
            cp = getattr(cue_points, f'cue_point_{i}', None)
            if cp:
                cp.time_ms = data['time_ms']
                cp.len_ms = data['len_ms'] if data['len_ms'] is not None else None
                cp.traktor_type = data['traktor_type']
                # Also update display fields if present
                try:
                    seconds = (data['time_ms'] / Decimal('1000'))
                    cp.time = f"{float(seconds):.3f}"
                except Exception:
                    pass
                cp.save()
