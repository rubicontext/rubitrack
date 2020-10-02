
from .models import Track, Transition, CurrentlyPlaying, TransitionType
from django.http import HttpResponse

#from django.http import HttpResponseRedirect
from django.shortcuts import render
import psycopg2 as psycopg
#from django import forms

#FILE_ICECAST_PLAYLIST=
MAX_PLAYLIST_HISTORY_SIZE=5

def display_currently_playing(request):
	currentTack = get_currently_playing_track(withRefresh=True)
	if(currentTack is None):
		return render(request, 'track/currently_playing.html', 
			{'currentTrack': None, 
			'playlistHistory':None, 
			'suggestionsManualInput':None,
			'suggestionsSameArtist' :None})

	else:
		playlistHistory = get_playing_track_list_history(withRefresh=False)
		suggestionsManualInput = get_suggestions_manual_input(currentTack)
		suggestionsSameArtist = get_suggestions_same_artist(currentTack)
		#playlistHistory = playlistHistory[1:10]
		return render(request, 'track/currently_playing.html', 
			{'currentTrack': currentTack, 
			'playlistHistory':playlistHistory, 
			'suggestionsManualInput':suggestionsManualInput,
			'suggestionsSameArtist' :suggestionsSameArtist})


def get_currently_playing_track(withRefresh=True):
	if(withRefresh):
		if(not refresh_currently_playing_from_log()):
			return None

	currentPlaylist = get_playing_track_list_history(withRefresh=False)
	currentTrack = currentPlaylist[len(currentPlaylist)-1].track
	#print(currentTrack)
	return currentTrack

def get_playing_track_list_history(withRefresh=True):
	if(withRefresh):
		if(not refresh_currently_playing_from_log()):
			return None
	currentPlaylist = CurrentlyPlaying.objects.order_by('date_played')
	if(len(currentPlaylist)> MAX_PLAYLIST_HISTORY_SIZE):
		currentPlaylist = currentPlaylist[len(currentPlaylist)-MAX_PLAYLIST_HISTORY_SIZE:len(currentPlaylist)]

	return currentPlaylist

def refresh_currently_playing_from_log():

	#file = open('/home/rubicontext/Downloads/playlist.log', 'r')
	file = open('/var/log/icecast2/playlist.log', 'r')
	lineList = file.readlines()
	if(len(lineList)<1):
		#print("Nothing to scrap in playlist log")
		return False
	lastLine = lineList[len(lineList)-1]
	#print("Current last line in log: ",lastLine) # already has newline


	#split the line to get the track title + artist
	indexSep = lastLine.find('-')
	artistName = lastLine[0:indexSep-1]
	trackTitle = lastLine[indexSep+2:len(lastLine)-1]

	#print("Track/Artist=",trackTitle,"/", artistName)
	#postgres_select_query = " SELECT id from track_track WHERE title like %s;"

	#postgres_select_query = 'SELECT * from track_track tt WHERE LOWER(tt.title) LIKE LOWER(%s)'
	#search_term = trackTitle[1:-1]
	#like_pattern = '%{}%'.format(search_term)
	#cursor.execute(postgres_select_query, (like_pattern,))
	#search_title = trackTitle[1:-1]
	search_title = trackTitle
	#print("search_title=", search_title)

	try:
		track = Track.objects.get(title=search_title)
	except Track.DoesNotExist:
		track = None

	#get the last played track to check if it changed
	lastTrackPlayed = get_currently_playing_track(withRefresh=False)
	if(track is None or lastTrackPlayed is None or track.id == lastTrackPlayed.id):
		#print ("No new record, still playing the same track...\n")
		return True

	currentPlay = CurrentlyPlaying()
	currentPlay.track=track
	currentPlay.save()
	#print ("1 Record inserted successfully into currently playing table\n")
	return True

#get last played row only
def get_more_played_history_row(request):
	lastTrackPlayed = get_currently_playing_track(withRefresh=False)
	refresh_currently_playing_from_log()
	#increment = int(request.GET['append_increment'])
	#increment_to = increment + 10
	currently_playing_track = CurrentlyPlaying.objects.order_by('-date_played')[0]
	if(lastTrackPlayed.id == currently_playing_track.track.id):
		return HttpResponse('')
	else:
		return render(request, 'track/get_more_played_history_row.html', {'currentTrack': currently_playing_track.track})

#get last five played tracks
def get_more_playlist_history_table(request):
	lastTrackPlayed = get_currently_playing_track(withRefresh=False)
	refresh_currently_playing_from_log()
	#increment = int(request.GET['append_increment'])
	#increment_to = increment + 10
	playlist_history_table_raw = CurrentlyPlaying.objects.order_by('date_played')
	if (len(playlist_history_table_raw) > 5):
		playlist_history_table = playlist_history_table_raw[len(playlist_history_table_raw)-5:len(playlist_history_table_raw)]
	else:
		playlist_history_table = playlist_history_table_raw
	#currently_playing_track = playlist_history_table[0]
	#if(lastTrackPlayed.id == currently_playing_track.track.id):
	#	return HttpResponse('')
	#else:
	return render(request, 'track/get_more_playlist_history_table.html', {'playlistHistory': playlist_history_table})

def get_more_currently_playing_title_block(request):
	currently_playing_track = CurrentlyPlaying.objects.order_by('-date_played')[0]
	return render(request, 'track/get_more_currently_playing_title_block.html', {'currentTrack': currently_playing_track.track})

def get_more_currently_playing_track_block(request):
	currently_playing_track = CurrentlyPlaying.objects.order_by('-date_played')[0]
	return render(request, 'track/get_more_currently_playing_track_block.html', {'currentTrack': currently_playing_track.track})

def get_suggestions_manual_input(track):
        suggestions = Transition.objects.filter(track_source=track)
        return suggestions

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


