
from .models import Track, TrackToTrack, CurrentlyPlaying
from django.http import HttpResponse

#from django.http import HttpResponseRedirect
from django.shortcuts import render
import psycopg2 as psycopg
#from django import forms

#FILE_ICECAST_PLAYLIST=
MAX_PLAYLIST_HISTORY_SIZE=5

def display_currently_playing(request):
	currentTack = get_currently_playing_track(withRefresh=True)
	playlistHistory = get_playing_track_list_history(withRefresh=False)
	#playlistHistory = playlistHistory[1:10]
	return render(request, 'track/currently_playing.html', {'currentTrack': currentTack, 'playlistHistory':playlistHistory})


def get_currently_playing_track(withRefresh=True):
	if(withRefresh):
		if(not refresh_currently_playing_from_log()):
			return None

	currentPlaylist = get_playing_track_list_history(withRefresh=False)
	currentTrack = currentPlaylist[len(currentPlaylist)-1].track
	print(currentTrack)
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
		print("Nothing to scrap in playlist log")
		return False
	lastLine = lineList[len(lineList)-1]
	#print("Current last line in log: ",lastLine) # already has newline


	#split the line to get the track title + artist
	indexSep = lastLine.find('-')
	artistName = lastLine[0:indexSep-1]
	trackTitle = lastLine[indexSep+2:len(lastLine)-1]

	print("Track/Artist=",trackTitle,"/", artistName)
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
		print("ERROR NO TRACK FOUND : ", search_title)

	#get the last played track to check if it changed
	lastTrackPlayed = get_currently_playing_track(withRefresh=False)
	if(track.id == lastTrackPlayed.id):
		print ("No new record, still playing the same track...\n")
		return True

	currentPlay = CurrentlyPlaying()
	currentPlay.track=track
	currentPlay.save()
	print ("1 Record inserted successfully into currently playing table\n")
	return True
	
def get_more_tables(request):
	lastTrackPlayed = get_currently_playing_track(withRefresh=False)
	refresh_currently_playing_from_log()
	#increment = int(request.GET['append_increment'])
	#increment_to = increment + 10
	currently_playing_track = CurrentlyPlaying.objects.order_by('-date_played')[0]
	if(lastTrackPlayed.id == currently_playing_track.track.id):
		return HttpResponse('')
	else:
		return render(request, 'track/get_more_tables.html', {'currently_playing_track': currently_playing_track})