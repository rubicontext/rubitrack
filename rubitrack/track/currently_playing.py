
from .models import Track, Transition, CurrentlyPlaying, TransitionType
from django.http import HttpResponse

#from django.http import HttpResponseRedirect
from django.shortcuts import render
import psycopg2 as psycopg
#from django import forms

#FILE_ICECAST_PLAYLIST=
MAX_PLAYLIST_HISTORY_SIZE=4

def display_currently_playing(request):
	currentTack = get_currently_playing_track(withRefresh=True)
	if(currentTack is None):
		return render(request, 'track/currently_playing.html', 
			{'currentTrack': None, 
			'playlistHistory':None, 
			'transitionsAfter':None,
			'transitionsBefore':None,
			'suggestionsSameArtist' :None})

	else:
		playlistHistory = get_playing_track_list_history(withRefresh=False)
		transitionsAfter = get_transitions_after(currentTack)
		transitionsBefore = get_transitions_before(currentTack)
		listTrackSuggestions = get_list_track_suggestions_auto(currentTack)
		#playlistHistory = playlistHistory[1:10]
		return render(request, 'track/currently_playing.html', 
			{'currentTrack': currentTack, 
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
		track = Track.objects.filter(title__icontains=search_title)[0]
		print("found a current track!", track.title)
	except Track.DoesNotExist:
		print("Error finding track by title:", search_title, '/')
		track = None

	#get the last played track to check if it changed
	lastTrackPlayed = get_currently_playing_track_from_db()

	#if None, first time for this user
	if(lastTrackPlayed is None):
		currentPlay = CurrentlyPlaying()
		currentPlay.track=track
		currentPlay.save()
		return True


	print("found a last track played in db!", lastTrackPlayed.title)
	if(track is None or track.id == lastTrackPlayed.id):
		#print ("No new record, still playing the same track...\n")
		return False

	currentPlay = CurrentlyPlaying()
	currentPlay.track=track
	currentPlay.save()
	return True

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
		currentPlaylist = currentPlaylist[0:len(currentPlaylist)-1]

	return currentPlaylist

#get last five played tracks
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
        return listTracks

def get_more_suggestion_auto_block(request):
		currentlyPlayingTrack = CurrentlyPlaying.objects.order_by('-date_played')[0]
		currentTrack = currentlyPlayingTrack.track
		listTracks = get_list_track_suggestions_auto(currentTrack)
		return render(request, 'track/get_more_suggestion_auto_block.html', {'listTrackSuggestions': listTracks})


