from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

from django.shortcuts import render

from datetime import datetime
import pytz

from track.suggestions import get_list_track_suggestions_auto

from .models import Track, Artist, Transition, CurrentlyPlaying
from .rubi_conf import (RUBI_ICECAST_PLAYLIST_FILE,
                        MAX_PLAYLIST_HISTORY_SIZE)

@login_required
def display_currently_playing(request):
    currentTrack = get_currently_playing_track(withRefresh=True)
    if currentTrack is None:
        return render(
            request,
            'track/currently_playing.html',
            {
                'currentTrack': None,
                'playlistHistory': None,
                'transitionsAfter': None,
                'transitionsBefore': None,
                'suggestionsSameArtist': None,
            },
        )

    else:
        playlistHistory = get_playing_track_list_history(withRefresh=False)
        transitionsAfter = get_transitions_after(currentTrack)
        transitionsBefore = get_transitions_before(currentTrack)
        listTrackSuggestions = get_list_track_suggestions_auto(currentTrack)
        return render(
            request,
            'track/currently_playing.html',
            {
                'currentTrack': currentTrack,
                'playlistHistory': playlistHistory,
                'transitionsAfter': transitionsAfter,
                'transitionsBefore': transitionsBefore,
                'listTrackSuggestions': listTrackSuggestions,
            },
        )


@login_required
def display_history_editing(request, trackId):
    currentTrack = Track.objects.get(id=trackId)
    if currentTrack is None:
        return render(
            request,
            'track/history_editing.html',
            {
                'currentTrack': None,
                'playlistHistory': None,
                'transitionsAfter': None,
                'transitionsBefore': None,
                'suggestionsSameArtist': None,
            },
        )

    else:
        playlistHistory = get_playing_track_list_history(withRefresh=False, removeLast=False, currentTrack=currentTrack)
        transitionsAfter = get_transitions_after(currentTrack)
        transitionsBefore = get_transitions_before(currentTrack)
        listTrackSuggestions = get_list_track_suggestions_auto(currentTrack)
        print("Edit history for track : ", currentTrack)
        return render(
            request,
            'track/history_editing.html',
            {
                'currentTrack': currentTrack,
                'playlistHistory': playlistHistory,
                'transitionsAfter': transitionsAfter,
                'transitionsBefore': transitionsBefore,
                'listTrackSuggestions': listTrackSuggestions,
            },
        )


def get_currently_playing_track(withRefresh=True):
    if withRefresh:
        refresh_currently_playing_from_log()
    return get_currently_playing_track_from_db()


def get_currently_playing_track_from_db():
    currentPlaylist = CurrentlyPlaying.objects.order_by('date_played')
    if len(currentPlaylist) > 0:
        currentTrack = currentPlaylist[len(currentPlaylist) - 1].track
        return currentTrack
    else:
        return None


def get_currently_playing_track_time_from_db():
    currentPlaylist = CurrentlyPlaying.objects.order_by('date_played')
    if len(currentPlaylist) > 0:
        currentTrackTime = currentPlaylist[len(currentPlaylist) - 1].date_played
        return currentTrackTime
    else:
        return None


def refresh_currently_playing_from_log():

    path_to_playlist_log = RUBI_ICECAST_PLAYLIST_FILE
    file = open(path_to_playlist_log, 'r')
    lineList = file.readlines()
    if len(lineList) < 1:
        print("Nothing to scrap in playlist log")
        return False

    # we check if the previous lines have been added from log to db
    lastDbPlayedTime = get_currently_playing_track_time_from_db()
    print("Current last time played in DB: ", lastDbPlayedTime)

    # new version to iterate on lines, to see if past tracks have been saved into DB
    with open(path_to_playlist_log) as playlistFile:
        for currentLine in playlistFile:

            # get time of log 08/Jan/2023:20:57:58 and place after
            indexSep = currentLine.find(' ')
            logTimeRaw = currentLine[0 : indexSep - 1]
            logTimeObject = datetime.strptime(logTimeRaw, '%d/%b/%Y:%H:%M:%S')

            # manage timezone for comparison
            utc = pytz.UTC
            logTimeObject = utc.localize(logTimeObject)

            if logTimeObject > lastDbPlayedTime:
                print(
                    'Last DB time (',
                    lastDbPlayedTime,
                    ') is anterior to previous logs time ==> saving past logs:',
                    currentLine,
                )
                save_track_played_to_db_from_log_line(currentLine)


def save_track_played_to_db_from_log_line(trackLineLog):
    #TODO refactor this
    # 08/Dec/2021:14:59:43 +0000|/|0|LALLA - Narcos  (Extended Remix) - Bm - 5
    # split the line to get the track title + artist
    indexSep = trackLineLog.find('-')
    artistNameTime = trackLineLog[0 : indexSep - 1]
    trackTitle = trackLineLog[indexSep + 2 : len(trackLineLog) - 1]

    # clean artist and time
    indexSepTime = artistNameTime.rfind('|')
    artistName = artistNameTime[indexSepTime + 1 : len(artistNameTime) - 1]

    ##V2 with mixed in key
    lastLineToProcess = trackLineLog
    countSep = lastLineToProcess.count('-')
    energy = None
    initialKey = None

    if countSep == 3:
        # mixed in key : LALLA - Narcos  (Extended Remix) - Bm - 5
        # energy
        indexSep = lastLineToProcess.rfind('-')
        energy = lastLineToProcess[indexSep + 2 : len(lastLineToProcess) - 1]
        lastLineToProcess = lastLineToProcess[0 : indexSep - 1]

        # key
        indexSep = lastLineToProcess.rfind('-')
        initialKey = lastLineToProcess[indexSep + 2 : len(lastLineToProcess) - 1]
        lastLineToProcess = lastLineToProcess[0 : indexSep - 1]

    # common fields
    # title
    indexSep = lastLineToProcess.rfind('-')
    trackTitle = lastLineToProcess[indexSep + 2 : len(lastLineToProcess)]
    lastLineToProcess = lastLineToProcess[0 : indexSep - 1]
    print("trackTitle : ", trackTitle)
    # print("to process :", lastLineToProcess)

    # artist
    indexSep = lastLineToProcess.rfind('|')
    artistName = lastLineToProcess[indexSep + 1 : len(lastLineToProcess)]
    lastLineToProcess = trackLineLog[0 : indexSep - 1]
    print("artistName : ", artistName)
    # print("to process :", lastLineToProcess)

    search_title = trackTitle
    track = get_track_by_title_and_artist_name(search_title, artistName)
    lastTrackPlayed = get_currently_playing_track_from_db()

    if lastTrackPlayed is not None and (track is None or track.id == lastTrackPlayed.id):
        return False

    # get time of log 08/Jan/2023:20:57:58 and place after
    indexSep = lastLineToProcess.find(' ')
    logTimeRaw = trackLineLog[0 : indexSep - 1]
    logTimeObject = datetime.strptime(logTimeRaw, '%d/%b/%Y:%H:%M:%S')

    currentPlay = CurrentlyPlaying()
    currentPlay.track = track
    currentPlay.date_played = logTimeObject
    currentPlay.save()
    return True


# get track from title and artist name
def get_track_by_title_and_artist_name(trackTitle, artistName):
    trackDb = None
    artistDb = None
    print("about to look for track:", trackTitle, "By artist :", artistName)
    artistList = Artist.objects.filter(name=artistName)
    # create artist if neeeded
    if len(artistList) < 1:
        # check for close matches by same artists
        artistList = Artist.objects.filter(name__icontains=artistName)
        if len(artistList) > 0:
            artistDb = artistList[0]
        else:
            artistDb = Artist()
            artistDb.name = artistName
            artistDb.save()
            print("WARNING Created new artist:", artistName)
    else:
        artistDb = artistList[0]

    return get_track_db_from_title_artist(trackTitle, artistDb)


def get_track_db_from_title_artist(trackTitle: str, artistDb: Artist):
    trackList = Track.objects.filter(title=trackTitle, artist=artistDb)
    if len(trackList) == 1:
        return trackList[0]

    if len(trackList) > 1:
        print("WARNING DUPLICATE track :", trackTitle, "By artist :", artistDb.name)
        return trackList[0]

    # no exact match found
    # check for close matches by same artists
    searchTitle = trackTitle.lstrip()
    trackList = Track.objects.filter(title__icontains=searchTitle, artist=artistDb)
    if len(trackList) > 0:
        print("FOUND with strip")
        return trackList[0]

    # happends with wierd formatting il log file
    searchTitle = trackTitle[:-1]
    trackList = Track.objects.filter(title__icontains=searchTitle, artist=artistDb)
    if len(trackList) > 0:
        print("FOUND with 1 char removed")
        return trackList[0]

    # create new track, should only happend if no import of collection
    print("WARNING Created new track, :", trackTitle)
    trackDb = Track()
    trackDb.title = trackTitle
    trackDb.artist = artistDb
    trackDb.save()
    return trackDb


# get last played row only
def get_more_played_history_row(request):
    lastTrackPlayed = get_currently_playing_track(withRefresh=False)
    currently_playing_track = CurrentlyPlaying.objects.order_by('-date_played')[0]
    if lastTrackPlayed.id == currently_playing_track.track.id:
        return HttpResponse('')
    else:
        return render(
            request, 'track/get_more_played_history_row.html', {'currentTrack': currently_playing_track.track}
        )


def get_playing_track_list_history(withRefresh=True, removeLast=True, currentTrack=None):
    if withRefresh:
        refresh_currently_playing_from_log()
    currentPlaylist = CurrentlyPlaying.objects.order_by('date_played')
    if len(currentPlaylist) > MAX_PLAYLIST_HISTORY_SIZE:
        currentPlaylist = currentPlaylist[len(currentPlaylist) - MAX_PLAYLIST_HISTORY_SIZE : len(currentPlaylist)]

    if len(currentPlaylist) > 1:
        if currentTrack is None:
            currentTrackHist = currentPlaylist[len(currentPlaylist) - 1]
            currentTrack = currentTrackHist.track

        # remove current from history
        if removeLast:
            currentPlaylist = currentPlaylist[0 : len(currentPlaylist) - 1]

        # add data if related
        for currentHistItem in currentPlaylist:
            if are_track_related(currentHistItem.track, currentTrack):
                currentHistItem.related_to_current_track = True
                currentHistItem.related_to_current_track_text = get_track_related_text(
                    currentHistItem.track, currentTrack
                )

    return reversed(currentPlaylist)


# get last five played tracks
@login_required
def get_more_playlist_history_table(request):
    playlist_history_table = get_playing_track_list_history(withRefresh=True)
    lastTrackPlayed = get_currently_playing_track(withRefresh=False)
    return render(
        request,
        'track/get_more_playlist_history_table.html',
        {'playlistHistory': playlist_history_table, 'currentTrack': lastTrackPlayed},
    )


def get_more_currently_playing_title_block(request):
    currently_playing_track = CurrentlyPlaying.objects.order_by('-date_played')[0]
    return render(
        request, 'track/get_more_currently_playing_title_block.html', {'currentTrack': currently_playing_track.track}
    )


def get_more_currently_playing_track_block(request):
    currently_playing_track = CurrentlyPlaying.objects.order_by('-date_played')[0]
    return render(
        request, 'track/get_more_currently_playing_track_block.html', {'currentTrack': currently_playing_track.track}
    )


def get_transitions_after(track):
    transitions = Transition.objects.filter(track_source=track)
    return transitions


def get_transitions_before(track):
    transitions = Transition.objects.filter(track_destination=track)
    return transitions


def get_more_suggestion_auto_block(request):
    currentlyPlayingTrack = CurrentlyPlaying.objects.order_by('-date_played')[0]
    currentTrack = currentlyPlayingTrack.track
    listTracks = get_list_track_suggestions_auto(currentTrack)
    return render(request, 'track/get_more_suggestion_auto_block.html', {'listTrackSuggestions': listTracks})


def get_more_transition_block(request):
    currentTrackDb = get_currently_playing_track(withRefresh=False)
    if request.method == 'GET' and 'currentTrackId' in request.GET:
        currentTrackFormId = request.GET['currentTrackId']
        if currentTrackFormId == str(currentTrackDb.id):
            return render(request, 'track/blank.html')

    transitionsBefore = get_transitions_before(currentTrackDb)
    transitionsAfter = get_transitions_after(currentTrackDb)
    print("TRANSITIONS (playing) found before/after", transitionsBefore, '/', transitionsAfter)
    return render(
        request,
        'track/get_more_transition_block.html',
        {'transitionsBefore': transitionsBefore, 'transitionsAfter': transitionsAfter, 'currentTrack': currentTrackDb},
    )


def get_more_transition_block_history(request, currentTrackId=None):
    if request.method == 'GET' and (
        'currentTrackId' in request.GET or 'trackSourceId' in request.GET or currentTrackId is not None
    ):
        if 'currentTrackId' in request.GET:
            currentTrackFormId = request.GET['currentTrackId']
        elif 'trackSourceId' in request.GET:
            currentTrackFormId = request.GET['trackSourceId']
        else:
            currentTrackFormId = currentTrackId

        currentTrackDb = Track.objects.get(pk=currentTrackFormId)
        if currentTrackDb is not None:
            transitionsBefore = get_transitions_before(currentTrackDb)
            transitionsAfter = get_transitions_after(currentTrackDb)
            return render(
                request,
                'track/get_more_transition_block.html',
                {
                    'transitionsBefore': transitionsBefore,
                    'transitionsAfter': transitionsAfter,
                    'currentTrack': currentTrackDb,
                },
            )
    print('ERROR TRACK NOT FOUND')
    return render(request, 'track/blank.html')


# check if two tracks are related
def are_track_related(trackSource, trackDestination):
    transitionList = Transition.objects.filter(track_source=trackSource, track_destination=trackDestination)
    if len(transitionList) > 0:
        return True
    return False


# get transition text for related tracks
def get_track_related_text(trackSource, trackDestination):
    transitionList = Transition.objects.filter(track_source=trackSource, track_destination=trackDestination)
    if len(transitionList) > 0:
        return transitionList[0].comment
    return None
