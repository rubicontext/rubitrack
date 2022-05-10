from django.contrib.auth.decorators import login_required
from .models import Track, Artist, Transition, CurrentlyPlaying, TransitionType
from django.http import HttpResponse

#from django.http import HttpResponseRedirect
from django.shortcuts import render
import psycopg2 as psycopg
from datetime import datetime 

#FILE_ICECAST_PLAYLIST=
MAX_PLAYLIST_HISTORY_SIZE=10
# MAX_PLAYLIST_HISTORY_SIZE_EXPANDED=10
MAX_SUGGESTIONS_AUTO_SIZE=20

@login_required
def display_currently_playing(request):
	currentTrack = get_currently_playing_track(withRefresh=True)
	if(currentTrack is None):
		return render(request, 'track/currently_playing.html', 
			{'currentTrack': None, 
			'playlistHistory':None, 
			'transitionsAfter':None,
			'transitionsBefore':None,
			'suggestionsSameArtist' :None})

	else:
		playlistHistory = get_playing_track_list_history(withRefresh=False)
		transitionsAfter = get_transitions_after(currentTrack)
		transitionsBefore = get_transitions_before(currentTrack)
		listTrackSuggestions = get_list_track_suggestions_auto(currentTrack)
		#playlistHistory = playlistHistory[1:10]
		return render(request, 'track/currently_playing.html', 
			{'currentTrack': currentTrack, 
			'playlistHistory':playlistHistory, 
			'transitionsAfter':transitionsAfter,
			'transitionsBefore' :transitionsBefore,
			'listTrackSuggestions' :listTrackSuggestions})

@login_required
def display_history_playing(request, trackId):
	currentTrack = Track.objects.get(id=trackId)
	if(currentTrack is None):
		return render(request, 'track/history_playing.html', 
			{'currentTrack': None, 
			'playlistHistory':None, 
			'transitionsAfter':None,
			'transitionsBefore':None,
			'suggestionsSameArtist' :None})

	else:
		playlistHistory = get_playing_track_list_history(withRefresh=False)
		transitionsAfter = get_transitions_after(currentTrack)
		transitionsBefore = get_transitions_before(currentTrack)
		listTrackSuggestions = get_list_track_suggestions_auto(currentTrack)
		#playlistHistory = playlistHistory[1:10]
		return render(request, 'track/history_playing.html', 
			{'currentTrack': currentTrack, 
			'playlistHistory':playlistHistory, 
			'transitionsAfter':transitionsAfter,
			'transitionsBefore' :transitionsBefore,
			'listTrackSuggestions' :listTrackSuggestions})

def get_currently_playing_track(withRefresh=True):
	if(withRefresh):
		refresh_currently_playing_from_log()
	return get_currently_playing_track_from_db()

def get_currently_playing_track_from_db():
	currentPlaylist = CurrentlyPlaying.objects.order_by('date_played')
	if(len(currentPlaylist) >0):
		currentTrack = currentPlaylist[len(currentPlaylist)-1].track
		return currentTrack
	else:
		return None

def refresh_currently_playing_from_log():

	#file = open('/home/rubicontext/Downloads/playlist.log', 'r')
	file = open('/var/log/icecast2/playlist.log', 'r')
	# file = open('c:/acar/perso/icecast.log', 'r')
	lineList = file.readlines()
	if(len(lineList)<1):
		#print("Nothing to scrap in playlist log")
		return False
	lastLine = lineList[len(lineList)-1]
	print("Current last line in log: ",lastLine) 

	#08/Dec/2021:14:59:43 +0000|/|0|LALLA - Narcos  (Extended Remix) - Bm - 5
	#split the line to get the track title + artist
	indexSep = lastLine.find('-')
	artistNameTime = lastLine[0:indexSep-1]
	trackTitle = lastLine[indexSep+2:len(lastLine)-1]

	#clean artist and time
	indexSepTime = artistNameTime.rfind('|')
	#print("sepTime", indexSepTime, "length", len(artistNameTime))
	artistName = artistNameTime[indexSepTime+1:len(artistNameTime)-1]

	##V2 with mixed in key
	
	lastLineToProcess = lastLine
	countSep = lastLineToProcess.count('-')

	if (countSep == 3):
		#mixed in key : LALLA - Narcos  (Extended Remix) - Bm - 5
		
		#energy
		indexSep = lastLineToProcess.rfind('-')
		energy = lastLineToProcess[indexSep+2:len(lastLineToProcess)-1]
		lastLineToProcess = lastLineToProcess[0:indexSep-1]
		print("energy : ", energy)
		print("to process :", lastLineToProcess)

		#key
		indexSep = lastLineToProcess.rfind('-')
		initialKey = lastLineToProcess[indexSep+2:len(lastLineToProcess)-1]
		lastLineToProcess = lastLineToProcess[0:indexSep-1]
		print("initialKey : ", initialKey)
		print("to process :", lastLineToProcess)

	else:
		#no key and energy, just titel - artist
		energy = None
		initialKey = None

	#common fields
	#title
	indexSep = lastLineToProcess.rfind('-')
	trackTitle = lastLineToProcess[indexSep+2:len(lastLineToProcess)]
	lastLineToProcess = lastLineToProcess[0:indexSep-1]
	print("trackTitle : ", trackTitle)
	print("to process :", lastLineToProcess)

	#artist
	indexSep = lastLineToProcess.rfind('|')
	artistName = lastLineToProcess[indexSep+1:len(lastLineToProcess)]
	lastLineToProcess = lastLine[0:indexSep-1]
	print("artistName : ", artistName)
	print("to process :", lastLineToProcess)

	#time played
	indexSep = lastLineToProcess.find(' +')
	dateTimePlayed = lastLineToProcess[0:indexSep]
	print("dateTimePlayed RAW : ", dateTimePlayed)
	# dateTimePlayed='08/Dec/2021:14:59:43'
	formatDate = datetime.strptime(dateTimePlayed, "%d/%b/%Y:%H:%M:%S")
	print("dateTimePlayed FORMAT : ", formatDate)

	#print("Track/Artist=",trackTitle,"/", artistName)
	#postgres_select_query = " SELECT id from track_track WHERE title like %s;"

	#postgres_select_query = 'SELECT * from track_track tt WHERE LOWER(tt.title) LIKE LOWER(%s)'
	#search_term = trackTitle[1:-1]
	#like_pattern = '%{}%'.format(search_term)
	#cursor.execute(postgres_select_query, (like_pattern,))
	#search_title = trackTitle[1:-1]
	search_title = trackTitle
	#print("search_title=", search_title)

	track = get_track_by_title_and_artist_name(search_title, artistName)
	#print("found a current track!", track.title)
	
	#get the last played track to check if it changed
	lastTrackPlayed = get_currently_playing_track_from_db()

	#if None, first time for this user
	if(lastTrackPlayed is None):
		currentPlay = CurrentlyPlaying()
		currentPlay.track=track
		currentPlay.save()
		return True


	#print("found a last track played in db!", lastTrackPlayed.title)
	if(track is None or track.id == lastTrackPlayed.id):
		#print ("No new record, still playing the same track...\n")
		return False

	currentPlay = CurrentlyPlaying()
	currentPlay.track=track
	currentPlay.save()
	return True

#get track from title and artist name
def get_track_by_title_and_artist_name(trackTitle, artistName):
	trackDb = None
	artistDb = None
	print("about to look for track:", trackTitle, "By artist :", artistName)
	artistList = Artist.objects.filter(name=artistName)
	#create artist if neeeded
	if(len(artistList) <1):
		#check for close matches by same artists
		artistList = Artist.objects.filter(name__icontains=artistName)
		if(len(artistList)>0):
			artistDb = artistList[0]
		else:
			artistDb = Artist()
			artistDb.name = artistName
			artistDb.save()
			#print("Created new artist:", artistName)
	else:
		artistDb = artistList[0]

	trackList = Track.objects.filter(title=trackTitle, artist=artistDb)
	if(len(trackList) <1):
		#no exact match found
		#check for close matches by same artists
		searchTitle = trackTitle.lstrip()
		trackList = Track.objects.filter(title__icontains=searchTitle, artist=artistDb)
		if(len(trackList)>0):
			trackDb = trackList[0]
		else:
			#create track
			trackDb = Track()
			trackDb.title = trackTitle
			trackDb.artist = artistDb
			trackDb.save()
			#print("Created new track:", trackTitle)
	else:
		trackDb = trackList[0]

	#print("Found or created trackDb:", trackDb)

	return trackDb


#get last played row only
def get_more_played_history_row(request):
	lastTrackPlayed = get_currently_playing_track(withRefresh=False)
	#refresh_currently_playing_from_log()
	#increment = int(request.GET['append_increment'])
	#increment_to = increment + 10
	currently_playing_track = CurrentlyPlaying.objects.order_by('-date_played')[0]
	if(lastTrackPlayed.id == currently_playing_track.track.id):
		return HttpResponse('')
	else:
		return render(request, 'track/get_more_played_history_row.html', {'currentTrack': currently_playing_track.track})

def get_playing_track_list_history(withRefresh=True):
	if(withRefresh):
		refresh_currently_playing_from_log()
	currentPlaylist = CurrentlyPlaying.objects.order_by('date_played')
	if(len(currentPlaylist)> MAX_PLAYLIST_HISTORY_SIZE):
		currentPlaylist = currentPlaylist[len(currentPlaylist)-MAX_PLAYLIST_HISTORY_SIZE:len(currentPlaylist)]
	#remove current from history
	if(len(currentPlaylist)>1):
		currentTrack = currentPlaylist[len(currentPlaylist)-1]
		currentPlaylist = currentPlaylist[0:len(currentPlaylist)-1]

		#add data if related
		for currentHistItem in currentPlaylist:
			if(are_track_related(currentHistItem.track, currentTrack.track)):
				currentHistItem.related_to_current_track=True

	return currentPlaylist

#get last five played tracks
@login_required
def get_more_playlist_history_table(request):
	playlist_history_table = get_playing_track_list_history(withRefresh=True)
	lastTrackPlayed = get_currently_playing_track(withRefresh=False)
	return render(request, 'track/get_more_playlist_history_table.html', {'playlistHistory': playlist_history_table, 'currentTrack':lastTrackPlayed})

def get_more_currently_playing_title_block(request):
	currently_playing_track = CurrentlyPlaying.objects.order_by('-date_played')[0]
	return render(request, 'track/get_more_currently_playing_title_block.html', {'currentTrack': currently_playing_track.track})

def get_more_currently_playing_track_block(request):
	currently_playing_track = CurrentlyPlaying.objects.order_by('-date_played')[0]
	return render(request, 'track/get_more_currently_playing_track_block.html', {'currentTrack': currently_playing_track.track})

def get_suggestions_manual_input(track):
        suggestions = Transition.objects.filter(track_source=track)
        return suggestions

def get_transitions_after(track):
        transitions = Transition.objects.filter(track_source=track)
        return transitions

def get_transitions_before(track):
        transitions = Transition.objects.filter(track_destination=track)
        return transitions

def get_suggestions_most_played_after(track):
        suggestions = Transition.objects.filter(track_source=track)
        return suggestions

def get_suggestions_same_artist(track):
	suggestions = None
	if(track is not None):
		suggestions = Track.objects.filter(artist=track.artist)
	return suggestions

def get_suggestions_same_genre(track):
        suggestions = Transition.objects.filter(track_source=track)
        return suggestions

def get_list_track_suggestions_auto(track):
        listTracks = Track.objects.filter(genre=track.genre, musical_key=track.musical_key)
        if(len(listTracks) > MAX_SUGGESTIONS_AUTO_SIZE):
        	listTracks = listTracks[0:MAX_SUGGESTIONS_AUTO_SIZE-1]
        #TODO filter on similar BPM!
        return listTracks

def get_more_suggestion_auto_block(request):
		currentlyPlayingTrack = CurrentlyPlaying.objects.order_by('-date_played')[0]
		currentTrack = currentlyPlayingTrack.track
		listTracks = get_list_track_suggestions_auto(currentTrack)
		return render(request, 'track/get_more_suggestion_auto_block.html', {'listTrackSuggestions': listTracks})

def get_more_transition_block(request):
	print("BEGINS get_more_transition_block")
	currentTrackDb = get_currently_playing_track(withRefresh=False)
	if(request.method  == 'GET' and 'currentTrackId' in request.GET):
		currentTrackFormId = request.GET['currentTrackId']
		print("found track id in REQ", currentTrackFormId, "old ID is:", currentTrackDb.id)
		if(currentTrackFormId == str(currentTrackDb.id)):
			#print('IDS are same!')
			return render(request, 'track/blank.html');

	transitionsBefore = get_transitions_before(currentTrackDb)
	transitionsAfter = get_transitions_after(currentTrackDb)
	print("ENDS found transition after", transitionsAfter)
	return render(request, 'track/get_more_transition_block.html', 
		{'transitionsBefore': transitionsBefore, 'transitionsAfter': transitionsAfter, 'currentTrack': currentTrackDb})
		

#check if two tracks are related
def are_track_related(trackSource, trackDestination):
	transitionList=Transition.objects.filter(track_source=trackSource, track_destination=trackDestination)
	if(len(transitionList)>0):
		return(True)
	return(False)


