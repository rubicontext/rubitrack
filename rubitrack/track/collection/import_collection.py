import datetime
from collections import defaultdict
from xml.dom.minidom import Element
import pytz
from decimal import Decimal, InvalidOperation
from typing import Dict, Optional, Set, Tuple

from django import forms
from django.db import transaction
from django.shortcuts import render

from track.playlist.playlist_transitions import get_order_rank
from ..models import Playlist, Track, Artist, Genre, Collection, CuePoint, TrackCuePoints
from ..musical_key.musical_key_utils import extract_musical_key_from_filename, normalize_musical_key_notation
from ..duplicate.display_duplicate import keys_are_equivalent

from django.contrib.auth.decorators import login_required

import xml.dom.minidom
import logging

logger = logging.getLogger(__name__)

UNKNOWN_ARTIST_NAME = "Unknown Artist"
MAX_COMMENT_LENGTH = 500
MAX_MUSICAL_KEY_LENGTH = 3
MAX_GENRE_LENGTH = 3


class UploadCollectionForm(forms.Form):
    file = forms.FileField()


class TrackImportIndex:
    """
    Index en mémoire des tracks existantes pour éviter les requêtes par ENTRY
    (l'import faisait plusieurs requêtes DB pour chaque morceau du fichier).
    """

    def __init__(self):
        all_tracks = list(Track.objects.all())
        self.by_artist_title: Dict[Tuple[int, str], Track] = {
            (t.artist_id, t.title): t for t in all_tracks
        }
        self.by_artist: Dict[int, list] = defaultdict(list)
        for t in all_tracks:
            self.by_artist[t.artist_id].append(t)
        self.by_audio_id: Dict[str, Track] = {t.audio_id: t for t in all_tracks if t.audio_id}

    def find(self, artist: Artist, title: str, audio_id: Optional[str]) -> Optional[Track]:
        """Retrouve une track existante, dans l'ordre de priorité historique:
        1. artist + titre exact
        1b. titre strippé ou enharmoniquement équivalent (Bbm ~ A#m) chez le même artiste
        2. audio_id
        """
        track = self.by_artist_title.get((artist.id, title))
        if track:
            return track

        title_stripped = title.strip()
        import_parts = title_stripped.split(' - ')
        for existing_track in self.by_artist[artist.id]:
            existing_stripped = existing_track.title.strip()
            if existing_stripped == title_stripped:
                logger.info(f"FOUND by stripped title: '{existing_track.title}' == '{title}'")
                return existing_track
            # e.g. "Song - A#m - 6" should match "Song - Bbm - 6"
            existing_parts = existing_stripped.split(' - ')
            if (len(existing_parts) >= 2 and len(import_parts) >= 2
                    and existing_parts[0] == import_parts[0]
                    and keys_are_equivalent(existing_parts[-2], import_parts[-2])):
                logger.info(f"FOUND by enharmonic key: '{existing_track.title}' ~ '{title}'")
                return existing_track

        if audio_id:
            track = self.by_audio_id.get(audio_id)
            if track:
                track.title = title
                return track
        return None

    def register(self, track: Track) -> None:
        """Ajoute/actualise une track (nouvelle ou re-titrée) dans les index."""
        self.by_artist_title[(track.artist_id, track.title)] = track
        if track not in self.by_artist[track.artist_id]:
            self.by_artist[track.artist_id].append(track)
        if track.audio_id:
            self.by_audio_id[track.audio_id] = track


@transaction.atomic
def handle_uploaded_file(file, user):

    xmldoc = xml.dom.minidom.parse(file)
    collection = xmldoc.getElementsByTagName('COLLECTION')
    entry_list = collection[0].getElementsByTagName('ENTRY')
    userCollection = get_default_collection_for_user(user)

    # Caches en mémoire: une requête par table au lieu de plusieurs par ENTRY
    artists_by_name = {a.name: a for a in Artist.objects.all()}
    genres_by_name = {g.name: g for g in Genre.objects.all()}
    track_index = TrackImportIndex()
    imported_tracks = []

    cptNewTracks = 0
    cptExistingTracks = 0
    # Evite les doublons d'ENTRY pour le même morceau (first-wins)
    processed_keys: Set[str] = set()
    for current_entry in entry_list:

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

        artist = get_artist_db_from_artist_name(artist_name_key, artists_by_name)
        genreName = get_genre_from_info(info)
        comment = get_comment_from_info(info)
        comment2 = get_rating_from_info(info)
        playcount = get_playcount_from_info(info)
        lastPlayedDate = get_last_played_date_from_info(info)
        musicalKey = get_musical_key_from_info(info)
        bitrate = get_bit_rate_from_info(info)
        bpm = get_bpm_from_info(current_entry)
        ranking = get_ranking_from_xml_info(info)
        genre = get_genre_db_from_genre_name(genreName, genres_by_name)

        # Check if TRACK exists or insert it
        track = track_index.find(artist, title, audio_id)
        if track:
            cptExistingTracks = cptExistingTracks + 1
        else:
            track = Track()
            track.title = title
            cptNewTracks = cptNewTracks + 1
            logger.info(f"NEW TRACK created: '{title}' - artist='{artist.name if artist else '?'}' - audio_id='{audio_id}'")

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
        track_index.register(track)
        imported_tracks.append(track)

        # Extract and save cue points
        extract_and_save_cue_points(current_entry, track)

    # Rattachement à la collection utilisateur en une seule passe (add est idempotent)
    if imported_tracks:
        userCollection.tracks.add(*imported_tracks)

    import_playlist_from_xml_doc(xmldoc, userCollection)

    return cptNewTracks, cptExistingTracks


def get_title_from_entry(current_entry):
    return current_entry.attributes['TITLE'].value


def get_audio_id_from_entry(current_entry):
    if 'AUDIO_ID' in current_entry.attributes:
        return current_entry.attributes['AUDIO_ID'].value
    else:
        logger.warning('WARNING no audio_id tag for entry :  %s', get_title_from_entry(current_entry))
        return None


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


def get_artist_db_from_artist_name(artistName: str, artists_by_name: Dict[str, Artist]) -> Artist:
    artist = artists_by_name.get(artistName)
    if artist is None:
        artist = Artist.objects.create(name=artistName)
        artists_by_name[artistName] = artist
    return artist


def get_genre_db_from_genre_name(genreName: Optional[str], genres_by_name: Dict[str, Genre]) -> Optional[Genre]:
    if genreName is None:
        return None
    genre = genres_by_name.get(genreName)
    if genre is None:
        genre = Genre.objects.create(name=genreName)
        genres_by_name[genreName] = genre
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
    - Les CuePoint existants sont mis à jour en place (ids stables entre imports)
    """
    cue_points_list = current_entry.getElementsByTagName('CUE_V2')
    if not cue_points_list:
        return

    track_cue_points, _ = TrackCuePoints.objects.get_or_create(track=track)

    seen_slots: Set[int] = set()
    new_cue_data: dict = {}

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

        new_cue_data[slot] = {
            'time': time_formatted,
            'type': name,
            'comment': comment,
            'traktor_type': traktor_type,
            'end_time': end_time_formatted,
            'duration': duration_seconds,
            'time_ms': start_ms_dec,
            'len_ms': len_ms_dec,
        }

    # Appliquer sur les 8 slots: update en place, création ou suppression
    for slot in range(1, 9):
        existing = getattr(track_cue_points, f'cue_point_{slot}')
        data = new_cue_data.get(slot)
        if data:
            if existing:
                for field, value in data.items():
                    setattr(existing, field, value)
                existing.save()
            else:
                setattr(track_cue_points, f'cue_point_{slot}', CuePoint.objects.create(**data))
        elif existing:
            existing.delete()
            setattr(track_cue_points, f'cue_point_{slot}', None)

    track_cue_points.save()


def import_playlist_from_xml_doc(xmldoc: Element, user_collection: Collection) -> None:

    playlists = xmldoc.getElementsByTagName('PLAYLISTS')
    playlist_list = playlists[0].getElementsByTagName('NODE')

    existing_playlist_count = 0
    new_playlist_count = 0
    track_found_count = 0
    track_not_found_count = 0

    # Index en mémoire file_path -> track (une seule requête pour toutes les playlists)
    tracks_by_file_path: Dict[str, Track] = {}
    for t in Track.objects.exclude(file_path__isnull=True).exclude(file_path=''):
        tracks_by_file_path.setdefault(t.file_path, t)

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

        found_tracks = []
        for current_entry in playlist_entry_list:
            for key in current_entry.getElementsByTagName('PRIMARYKEY'):
                file_path = key.attributes['KEY'].value

                track = tracks_by_file_path.get(file_path)
                if track is None:
                    track_not_found_count = track_not_found_count + 1
                    logger.warning('WARNING - Track not found for file_path:  %s', file_path)
                    continue

                track_found_count = track_found_count + 1
                track_ids.append(track.id)
                found_tracks.append(track)

        if found_tracks:
            playlist.tracks.add(*found_tracks)
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
