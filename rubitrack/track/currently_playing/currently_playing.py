from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

from django.shortcuts import render

from datetime import datetime
import pytz

from .suggestions import get_list_track_suggestions_auto
from .suggestions_block_view import get_suggestions_for_track
from ..playlist.playlist_context import get_next_tracks_in_playlists
from track.playlist.playlist_transitions import get_playlists_by_track_id, SEPARATOR_TRACK_ID
from ..constants import REFRESH_INTERVAL_CURRENTLY_PLAYING_MS

from ..models import Track, Transition, CurrentlyPlaying, Config
from ..constants import REFRESH_INTERVAL_CURRENTLY_PLAYING_MS
from ..track_db_service import (
    are_track_related,
    get_track_related_text,
    get_track_by_title_and_artist_name,
    get_currently_playing_track_from_db,
    get_currently_playing_track_time_from_db,
)

BLANK_TEMPLATE = 'track/blank.html'


def get_cue_points_times_for_track(track, slots: int = 8):
    """Return a list of cue point times indexed by slot number (1..slots).
    Each position i reflects cue_point_i (1-based). Missing or empty -> '-'.
    """
    result = ['-'] * slots
    if not track:
        return result
    try:
        if hasattr(track, 'cue_points') and track.cue_points:
            # Access each numbered attribute directly to keep alignment
            for i in range(1, slots + 1):
                cp = getattr(track.cue_points, f'cue_point_{i}', None)
                if cp:
                    time_val = getattr(cp, 'time', None)
                    result[i - 1] = time_val if time_val else '-'
    except Exception:
        pass
    return result

# New structured helper
def get_cue_points_slots_for_track(track, slots: int = 8):
    """Return list of dicts [{'slot':i,'time':..., 'exists':bool}] for slots 1..n"""
    slots_list = []
    if not track or not hasattr(track, 'cue_points') or not track.cue_points:
        return [{'slot': i, 'time': '-', 'exists': False} for i in range(1, slots + 1)]
    for i in range(1, slots + 1):
        cp = getattr(track.cue_points, f'cue_point_{i}', None)
        if cp:
            time_val = getattr(cp, 'time', None) or '-'
            slots_list.append({'slot': i, 'time': time_val, 'exists': True})
        else:
            slots_list.append({'slot': i, 'time': '-', 'exists': False})
    return slots_list

# Non-regressive helper to get cue points times without milliseconds
# Does not change existing behavior; safe to call where display without ms is needed

def get_cue_points_times_for_track_no_ms(track, slots: int = 8):
    """Return a list of cue point times (without milliseconds) indexed by slot number (1..slots).
    Each position i reflects cue_point_i (1-based). Missing or empty -> '-'.
    """
    result = ['-'] * slots
    if not track:
        return result
    try:
        if hasattr(track, 'cue_points') and track.cue_points:
            for i in range(1, slots + 1):
                cp = getattr(track.cue_points, f'cue_point_{i}', None)
                if cp:
                    # Prefer model helper if available, fallback to raw time
                    time_val = cp.get_time_without_ms() if hasattr(cp, 'get_time_without_ms') else (cp.time or '-')
                    result[i - 1] = time_val if time_val else '-'
    except Exception:
        pass
    return result

@login_required
def display_currently_playing(request):
    current_track = get_currently_playing_track(with_refresh=True)
    if current_track is None:
        return render(
            request,
            'track/currently_playing/currently_playing.html',
            {
                'currentTrack': None,
                'playlistHistory': None,
                'transitionsAfter': None,
                'transitionsBefore': None,
                'suggestionsSameArtist': None,
            },
        )
    else:
        playlist_history = get_playing_track_list_history(with_refresh=False)
        transitions_after = get_transitions_after(current_track)
        transitions_before = get_transitions_before(current_track)
        list_track_suggestions = get_list_track_suggestions_auto(current_track)
        # Ajout : playlists contenant la track
        playlists_with_track = get_playlists_by_track_id(current_track.id)
        
        # Prépare une liste de 8 time cue points (centralisé)
        cue_points_times = get_cue_points_times_for_track_no_ms(current_track)
        cue_points_slots = get_cue_points_slots_for_track(current_track)
        return render(
            request,
            'track/currently_playing/currently_playing.html',
            {
                'currentTrack': current_track,
                'playlistHistory': playlist_history,
                'transitionsAfter': transitions_after,
                'transitionsBefore': transitions_before,
                'listTrackSuggestions': list_track_suggestions,
                'playlistsWithTrack': playlists_with_track,
                'refreshInterval': REFRESH_INTERVAL_CURRENTLY_PLAYING_MS,
                'cue_points_times': cue_points_times,
                'cue_points_slots': cue_points_slots,
            },
        )


@login_required
def display_history_editing(request, track_id):
    current_track = Track.objects.get(id=track_id)
    if current_track is None:
        return render(
            request,
            'track/currently_playing/history_editing.html',
            {
                'currentTrack': None,
                'playlistHistory': None,
                'transitionsAfter': None,
                'transitionsBefore': None,
                'suggestionsSameArtist': None,
            },
        )
    else:
        playlist_history = get_playing_track_list_history(with_refresh=False, remove_last=False, current_track=current_track)
        transitions_after = get_transitions_after(current_track)
        transitions_before = get_transitions_before(current_track)
        list_track_suggestions = get_list_track_suggestions_auto(current_track)
        # Nouvelles suggestions interactives (tri par playcount décroissante par défaut)
        suggestions = get_suggestions_for_track(current_track.id, sort_by='playcount', sort_order='desc')
        # Ajout : playlists contenant la track
        playlists_with_track = get_playlists_by_track_id(current_track.id)
        # Ajout : tracks suivantes dans les playlists
        next_tracks_in_playlists = get_next_tracks_in_playlists(current_track.id)
        # Prépare une liste de 8 time cue points (centralisé)
        cue_points_times = get_cue_points_times_for_track_no_ms(current_track)
        cue_points_slots = get_cue_points_slots_for_track(current_track)
        config = Config.get_config()
        print("Edit history for track :", current_track)
        return render(
            request,
            'track/currently_playing/history_editing.html',
            {
                'currentTrack': current_track,
                'playlistHistory': playlist_history,
                'transitionsAfter': transitions_after,
                'transitionsBefore': transitions_before,
                'listTrackSuggestions': list_track_suggestions,
                'suggestions': suggestions,
                'playlistsWithTrack': playlists_with_track,
                'nextTracksInPlaylists': next_tracks_in_playlists,
                'cue_points_times': cue_points_times,
                'cue_points_slots': cue_points_slots,
                'all_tracks': Track.objects.order_by('title','artist__name').only('id','title','artist__name'),
                'default_ranking_min': config.default_ranking_min,
            },
        )


def get_currently_playing_track(with_refresh=True):
    if with_refresh:
        refresh_currently_playing_from_log()
    return get_currently_playing_track_from_db()


def refresh_currently_playing_from_log():
    config = Config.get_config()
    path_to_playlist_log = config.rubi_icecast_playlist_file
    file = open(path_to_playlist_log, 'r')
    line_list = file.readlines()
    if len(line_list) < 1:
        print("Nothing to scrap in playlist log")
        return False

    # we check if the previous lines have been added from log to db
    last_db_played_time = get_currently_playing_track_time_from_db()
    print("Current last time played in DB:", last_db_played_time)

    # new version to iterate on lines, to see if past tracks have been saved into DB
    with open(path_to_playlist_log) as playlist_file:
        for current_line in playlist_file:

            #get time of log 08/Jan/2023:20:57:58
            parts = get_log_parts_from_log_line(current_line)
            if not parts:
                continue
            log_time_object = get_log_time_object_from_log_parts(parts)

            # manage timezone for comparison
            utc = pytz.UTC
            log_time_object = utc.localize(log_time_object)

            if log_time_object > last_db_played_time:
                print(
                    'Last DB time (',
                    last_db_played_time,
                    ') is anterior to previous logs time ==> saving past logs:',
                    current_line,
                )
                save_track_played_to_db_from_log_line(current_line)


def save_track_played_to_db_from_log_line(track_line_log):
    # Refactored parsing for robustness and clarity
    # Example log: 08/Dec/2021:14:59:43 +0000|/|0|LALLA - Narcos  (Extended Remix) - Bm - 5\n
    try:
        # Remove trailing newline and split on '|'
        parts = get_log_parts_from_log_line(track_line_log)
        if not parts:
            return False

        # Get time
        log_time_object = get_log_time_object_from_log_parts(parts)

        # Get the track info part (after last '|')
        track_info = parts[-1].strip()
        # Split on ' - ' (with spaces)
        track_fields = [f.strip() for f in track_info.split(' - ')]

        artist_name = None
        track_title = None
        initial_key = None
        energy = None

        if len(track_fields) == 2:
            # Format: ARTIST - TITLE
            artist_name = track_fields[0]
            track_title = track_fields[1]
        elif len(track_fields) == 4:
            # Format: ARTIST - TITLE - KEY - ENERGY
            artist_name = track_fields[0]
            track_title = f"{track_fields[1]} - {track_fields[2]} - {track_fields[3]}"
            initial_key = track_fields[2]
            energy = track_fields[3]
        else:
            print("Unexpected track field count:", track_fields)
            return False

        print(f"track_title : {track_title}")
        print(f"artist_name : {artist_name}")
        if initial_key:
            print(f"initial_key : {initial_key}")
        if energy:
            print(f"energy : {energy}")

        search_title = track_title
        track = get_track_by_title_and_artist_name(search_title, artist_name)
        last_track_played = get_currently_playing_track_from_db()

        if last_track_played is not None and (track is None or track.id == last_track_played.id):
            return False

        # Save to DB
        current_play = CurrentlyPlaying()
        current_play.track = track
        current_play.date_played = log_time_object
        current_play.save()
        return True
    except Exception as e:
        print("Error parsing log line:", track_line_log, e)
        return False

def get_log_time_object_from_log_parts(parts):
    log_time_raw = parts[0].split(' ')[0]
    log_time_object = datetime.strptime(log_time_raw, '%d/%b/%Y:%H:%M:%S')
    return log_time_object

def get_log_parts_from_log_line(track_line_log):
    line = track_line_log.strip()
    parts = line.split('|')
    if len(parts) < 4:
        print("Log line format error:", line)
        parts = None
    return parts


# get last played row only
def get_more_played_history_row(request):
    last_track_played = get_currently_playing_track(with_refresh=False)
    currently_playing_track = CurrentlyPlaying.objects.order_by('-date_played')[0]
    if last_track_played.id == currently_playing_track.track.id:
        return HttpResponse('')
    else:
        return render(
            request, 'track/currently_playing/get_more_played_history_row.html', {'currentTrack': currently_playing_track.track}
        )


@login_required
def get_more_playlist_history_table(request):
    playlist_history_table = get_playing_track_list_history(with_refresh=True)
    last_track_played = get_currently_playing_track(with_refresh=False)
    return render(
        request,
        'track/playlists/get_more_playlist_history_table.html',
        {'playlistHistory': playlist_history_table, 'currentTrack': last_track_played},
    )


def get_more_currently_playing_title_block(request):
    currently_playing_track = CurrentlyPlaying.objects.order_by('-date_played')[0]
    return render(
        request, 'track/currently_playing/get_more_currently_playing_title_block.html', {'currentTrack': currently_playing_track.track}
    )


def get_more_currently_playing_track_block(request):
    currently_playing_track = CurrentlyPlaying.objects.order_by('-date_played')[0]
    return render(
        request, 'track/currently_playing/get_more_currently_playing_track_block.html', {'currentTrack': currently_playing_track.track}
    )


def get_more_suggestion_auto_block(request):
    currently_playing_track = CurrentlyPlaying.objects.order_by('-date_played')[0]
    current_track = currently_playing_track.track
    list_track_suggestions = get_list_track_suggestions_auto(current_track)
    return render(request, 'track/currently_playing/get_more_suggestion_auto_block.html', {'listTrackSuggestions': list_track_suggestions})


def get_more_transition_block(request):
    current_track_db = get_currently_playing_track(with_refresh=False)
    if request.method == 'GET' and 'currentTrackId' in request.GET:
        current_track_form_id = request.GET['currentTrackId']
        if current_track_form_id == str(current_track_db.id):
            return render(request, BLANK_TEMPLATE)

    transitions_before = get_transitions_before(current_track_db)
    transitions_after = get_transitions_after(current_track_db)
    cue_points_times = get_cue_points_times_for_track_no_ms(current_track_db)
    cue_points_slots = get_cue_points_slots_for_track(current_track_db)
    return render(
        request,
        'track/currently_playing/get_more_transition_block_history.html',
        {
            'transitionsBefore': transitions_before,
            'transitionsAfter': transitions_after,
            'currentTrack': current_track_db,
            'cue_points_times': cue_points_times,
            'cue_points_slots': cue_points_slots,
        },
    )


def get_more_transition_block_history(request, current_track_id=None):
    if request.method == 'GET' and (
        'currentTrackId' in request.GET or 'trackSourceId' in request.GET or current_track_id is not None
    ):
        if 'currentTrackId' in request.GET:
            current_track_form_id = request.GET['currentTrackId']
        elif 'trackSourceId' in request.GET:
            current_track_form_id = request.GET['trackSourceId']
        else:
            current_track_form_id = current_track_id

        current_track_db = Track.objects.get(pk=current_track_form_id)
        if current_track_db is not None:
            transitions_before = get_transitions_before(current_track_db)
            transitions_after = get_transitions_after(current_track_db)
            cue_points_times = get_cue_points_times_for_track_no_ms(current_track_db)
            cue_points_slots = get_cue_points_slots_for_track(current_track_db)

            return render(
                request,
                'track/currently_playing/get_more_transition_block_history.html',
                {
                    'transitionsBefore': transitions_before,
                    'transitionsAfter': transitions_after,
                    'currentTrack': current_track_db,
                    'cue_points_times': cue_points_times,
                    'cue_points_slots': cue_points_slots,
                },
            )
    print('ERROR TRACK NOT FOUND')
    return render(request, BLANK_TEMPLATE)


def get_playing_track_list_history(with_refresh=True, remove_last=True, current_track=None):
    if with_refresh:
        refresh_currently_playing_from_log()
    current_playlist = CurrentlyPlaying.objects.order_by('date_played')
    
    config = Config.get_config()
    max_history_size = config.max_playlist_history_size
    
    if len(current_playlist) > max_history_size:
        current_playlist = current_playlist[len(current_playlist) - max_history_size : len(current_playlist)]

    if len(current_playlist) > 1:
        if current_track is None:
            current_track_hist = current_playlist[len(current_playlist) - 1]
            current_track = current_track_hist.track

        # remove current from history
        if remove_last:
            current_playlist = current_playlist[0 : len(current_playlist) - 1]

        # add data if related
        for current_hist_item in current_playlist:
            if are_track_related(current_hist_item.track, current_track):
                current_hist_item.related_to_current_track = True
                current_hist_item.related_to_current_track_text = get_track_related_text(
                    current_hist_item.track, current_track
                )

    return reversed(current_playlist)


def get_transitions_after(track):
    transitions = Transition.objects.filter(track_source=track).exclude(track_source_id=SEPARATOR_TRACK_ID)
    return transitions


def get_transitions_before(track):
    transitions = Transition.objects.filter(track_destination=track).exclude(track_destination_id=SEPARATOR_TRACK_ID)
    return transitions


@login_required
def get_all_currently_playing_data(request):
    """
    Récupère toutes les données pour la page currently_playing en un seul appel
    pour éviter les multiples requêtes AJAX et optimiser le rafraîchissement
    """
    current_track = get_currently_playing_track(with_refresh=True)
    if current_track is None:
        return render(request, BLANK_TEMPLATE)
    
    playlist_history = get_playing_track_list_history(with_refresh=False)
    transitions_after = get_transitions_after(current_track)
    transitions_before = get_transitions_before(current_track)
    list_track_suggestions = get_list_track_suggestions_auto(current_track)
    playlists_with_track = get_playlists_by_track_id(current_track.id)
    
    # Prépare une liste de 8 time cue points (centralisé)
    cue_points_times = get_cue_points_times_for_track_no_ms(current_track)
    cue_points_slots = get_cue_points_slots_for_track(current_track)
    return render(
        request,
        'track/currently_playing/get_all_currently_playing_data.html',
        {
            'currentTrack': current_track,
            'playlistHistory': playlist_history,
            'transitionsAfter': transitions_after,
            'transitionsBefore': transitions_before,
            'listTrackSuggestions': list_track_suggestions,
            'playlistsWithTrack': playlists_with_track,
            'cue_points_times': cue_points_times,
            'cue_points_slots': cue_points_slots,
        },
    )


@login_required
def ajax_cue_points(request):
    """
    Endpoint AJAX pour récupérer les cue points d'une track
    """
    from django.http import JsonResponse
    from ..models import TrackCuePoints
    
    track_id = request.GET.get('track_id')
    if not track_id:
        return JsonResponse({'error': 'track_id required'}, status=400)
    
    try:
        track = Track.objects.get(id=track_id)
        track_cue_points = TrackCuePoints.objects.get(track=track)
        
        # Construire la liste des cue points actifs
        cue_points_data = []
        for i in range(1, 9):
            cue_point = getattr(track_cue_points, f'cue_point_{i}')
            if cue_point:
                cue_points_data.append({
                    'number': i,
                    'time': cue_point.time if cue_point.time is not None else '-',
                    'type': cue_point.type or '',
                    'comment': cue_point.comment or ''
                })
        
        return JsonResponse({
            'success': True,
            'cue_points': cue_points_data,
            'compact_text': track.get_track_cue_points_text()
        })
        
    except Track.DoesNotExist:
        return JsonResponse({'error': 'Track not found'}, status=404)
    except TrackCuePoints.DoesNotExist:
        return JsonResponse({'success': True, 'cue_points': [], 'compact_text': ''})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

