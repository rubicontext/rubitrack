
from .models import Track, TrackToTrack, CurrentlyPlaying

#from django.http import HttpResponseRedirect
from django.shortcuts import render
import psycopg2 as psycopg
#from django import forms

#FILE_ICECAST_PLAYLIST=

def display_currently_playing(request):
	currentTack = get_currently_playing_track()
	return render(request, 'track/currently_playing.html', {'currentTrack': currentTack})


def get_currently_playing_track():
	refresh_currently_playing_from_log()
	currentPlaylist = CurrentlyPlaying.objects.order_by('-date_played')
	currentTrack = currentPlaylist[0].track
	print(currentTrack)
	return currentTrack

def refresh_currently_playing_from_log():

	#file = open('/home/rubicontext/Downloads/playlist.log', 'r')
	file = open('/var/log/icecast2/playlist.log', 'r')
	lineList = file.readlines()
	lastLine = lineList[len(lineList)-1]
	print("Current last line in log: ",lastLine) # already has newline


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
	print("search_title=", search_title)

	try:
		track = Track.objects.get(title=search_title)
	except Track.DoesNotExist:
		print("ERROR NO TRACK FOUND : ", search_title)

	currentPlay = CurrentlyPlaying()
	currentPlay.track=track
	currentPlay.save()

	#cursor.execute(postgres_select_query, (trackTitle,))
	#track_records = cursor.fetchall()

	#postgres_insert_query = """ INSERT INTO track_currentlyplaying (date_played, track_id) VALUES (%s,%s)"""
	#current_time = datetime.now()
	#track_id = 1
	#record_to_insert = (current_time, track_id)
	#cursor.execute(postgres_insert_query, record_to_insert)

	#connection.commit()
	#count = cursor.rowcount
	print ("1 Record inserted successfully into currently playing table")
	