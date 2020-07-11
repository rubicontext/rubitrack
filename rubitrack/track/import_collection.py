from django import forms
from django.http import HttpResponseRedirect
from django.shortcuts import render
from .models import Track, Artist, Genre
#from .forms import UploadFileForm
from django.shortcuts import get_object_or_404

import xml.dom.minidom
#from .tt_utils import traverseTree
import datetime

UNKNOWN_ARTIST_NAME = "Unknown Artist"
MAX_COMMENT_LENGTH = 500
MAX_GENRE_LENGTH = 3

class UploadCollectionForm(forms.Form):
    #title = forms.CharField(max_length=50)
    file = forms.FileField()

# Imaginary function to handle an uploaded file.
#from somewhere import handle_uploaded_file

def handle_uploaded_file(file):
	#print('xml parsing BEGINs')
	xmldoc = xml.dom.minidom.parse(file)
	values = []
	#pk_list = xmldoc.getElementsByTagName('KEY')

	collection = xmldoc.getElementsByTagName('COLLECTION')
	#print("COLLECTION: ", collection)

	entry_list = collection[0].getElementsByTagName('ENTRY')
	#print("ENTRY LIST: ", entry_list)

	key_list = entry_list[0].getElementsByTagName('KEY')
	#print("TRACK: ", key_list)

	elements = []
	cptNewTracks = 0
	cptExistingTracks = 0
	for current_entry in entry_list :
		#print(current_entry)
		#print()
		title = current_entry.attributes['TITLE'].value
		#artistName = current_entry.attributes['ARTIST'].value
		if('ARTIST' in current_entry.attributes):
			artistName = current_entry.attributes['ARTIST'].value
		else:
			artistName=UNKNOWN_ARTIST_NAME
		#print("TRACK: ", title, "Artist: ", artistName)

		location = current_entry.getElementsByTagName('LOCATION')
		#print("LOCATION: ", location)
		info = current_entry.getElementsByTagName('INFO')
		#print("INFO: ", info)
		
		#comment
		if('GENRE' in info[0].attributes):
			genreName = info[0].attributes['GENRE'].value
			if(len(genreName)>MAX_GENRE_LENGTH):
				genreName=genreName[0:MAX_GENRE_LENGTH]
		else:
			genreName = None

		#comment
		if('COMMENT' in info[0].attributes):
			comment = info[0].attributes['COMMENT'].value
			if(len(comment)>MAX_COMMENT_LENGTH):
				comment=comment[0:MAX_COMMENT_LENGTH]
		else:
			comment = ''
		
		#comment2
		if('RATING' in info[0].attributes):
			comment2 = info[0].attributes['RATING'].value
		else:
			comment2 = ''
		#playcount
		if('PLAYCOUNT' in info[0].attributes):
			playcount = info[0].attributes['PLAYCOUNT'].value
		else:
			playcount = 0

		#last played
		if('LAST_PLAYED' in info[0].attributes):
			lastPlayedDateStr = info[0].attributes['LAST_PLAYED'].value
			lastPlayedDate = datetime.datetime.strptime(lastPlayedDateStr, '%Y/%m/%d').strftime('%Y-%m-%d')
		else:
			lastPlayedDate = None

		#last played
		if('IMPORT_DATE' in info[0].attributes):
			importDateStr = info[0].attributes['IMPORT_DATE'].value
			importDate = datetime.datetime.strptime(importDateStr, '%Y/%m/%d').strftime('%Y-%m-%d')
		else:
			importDate = None
				
		#musicalKey
		if('KEY' in info[0].attributes):
			musicalKey = info[0].attributes['KEY'].value
		else:
			musicalKey = 0

		if('BITRATE' in info[0].attributes):
			bitrate = info[0].attributes['BITRATE'].value
		else:
			bitrate = 0

		#playcount = info[0].attributes['PLAYCOUNT'].value
		#musicalKey = info[0].attributes['KEY'].value
		#bitrate = info[0].attributes['BITRATE'].value
		tempo = current_entry.getElementsByTagName('TEMPO')
		if(len(tempo)>0 and ('BPM' in tempo[0].attributes)):
			bpm = tempo[0].attributes['BPM'].value
		else:
			bpm = None

		#convert ranking from traktor (0-255) to regular 1-5 star system
		if('RANKING' in info[0].attributes):
			rankingTraktor = info[0].attributes['RANKING'].value
			if(rankingTraktor==255):
				ranking=5
			elif(rankingTraktor==204):
				ranking=4
			elif(rankingTraktor==153):
				ranking=3
			elif(rankingTraktor==99):
				ranking=2
			elif(rankingTraktor==51):
				ranking=1
			else:
				ranking=0
		else:
			ranking=None

		#check if ARTIST exists, or insert it
		#ArtistDb = Artist.objects.get(name=artistName)
		try:
			ArtistDb = Artist.objects.get(name=artistName)
			artist = ArtistDb
			#print("Found existing artist : ", artistName)
		except Artist.DoesNotExist:
			artist = Artist()
			artist.name=artistName
			artist.save()
			#print("Created new artist : ", artistName)
		
		#check if GENRE exists, or insert it
		if(genreName is not None):
			try:
				GenreDb = Genre.objects.get(name=genreName)
				genre = GenreDb
				#print("Found existing genre : ", genreName)
			except Genre.DoesNotExist:
				genre = Genre()
				genre.name=genreName
				genre.save()
				#print("Created new genre : ", genreName)
		else:
			genre=None

		#Check if TRACK exists or insert it
		try:
			TrackDb = Track.objects.get(title=title)
			track = TrackDb
			cptExistingTracks = cptExistingTracks+1
			#print("Found existing track : ", title)
		except Track.DoesNotExist:
			track = Track()
			track.title=title
			#track.save()
			cptNewTracks = cptNewTracks+1
			#print("Created new track : ", title)
		
		#update track infos
		track.bpm=666 #FOR DEBUG AND PURGE
		#track.bpm=bpm
		track.artist=artist
		track.genre=genre
		track.comment=comment
		track.comment2=comment2
		track.ranking=ranking
		track.playcount=playcount
		track.date_collection=importDate
		track.date_last_played=lastPlayedDate
		track.musical_key=musicalKey
		track.bitrate=bitrate
		track.bpm=bpm

		#print('About to save track with artist :', artist)
		track.save() #force save to add children

	#print('xml parsing DONE!')
	return cptNewTracks, cptExistingTracks

	#traverseTree(xml.documentElement)


def upload_file(request):
    if request.method == 'POST':
        form = UploadCollectionForm(request.POST, request.FILES)
        if form.is_valid():
        	#print('Form is valid!')
        	cptNewTracks, cptExistingTracks = handle_uploaded_file(request.FILES['file'])
        	#return HttpResponseRedirect('/admin/')
        	return render(request, 'track/import_collection.html', {'form': form, 'nb_new_tracks': cptNewTracks, 'nb_existing_tracks':cptExistingTracks, 'submitted':True})
    else:
        form = UploadCollectionForm()
    return render(request, 'track/import_collection.html', {'form': form})

