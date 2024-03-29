from django import forms
from django.http import HttpResponseRedirect
from django.shortcuts import render
from .models import Track, Artist, Genre, Collection
#from .forms import UploadFileForm
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required

import xml.dom.minidom
#from .tt_utils import traverseTree
import datetime

UNKNOWN_ARTIST_NAME = "Unknown Artist"
MAX_COMMENT_LENGTH = 500
MAX_MUSICAL_KEY_LENGTH = 3
MAX_GENRE_LENGTH = 3

class UploadCollectionForm(forms.Form):
    #title = forms.CharField(max_length=50)
    file = forms.FileField()

# Imaginary function to handle an uploaded file.
#from somewhere import handle_uploaded_file

def handle_uploaded_file(file, user):
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

	#get or init a collection object for this user
	userCollection = get_default_collection_for_user(user)

	elements = []
	cptNewTracks = 0
	cptExistingTracks = 0
	for current_entry in entry_list :
		#print(current_entry)
		#print(current_entry.attributes)
		title = current_entry.attributes['TITLE'].value

		#TESTS sur audio ID
		if('AUDIO_ID' in current_entry.attributes):
			audio_id=current_entry.attributes['AUDIO_ID'].value
		else:
			audio_id = None
			print('WARNING no audio_id tag for entry : ', title)
		# if(title=='Au pas, au trot, au galop'):
		# 	print('AU PAS ID : ', audio_id)
		
		#Si pas de audio ID 

		
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

		#sample auto imported must be ignored
		if not info:
			continue
		
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
			if(len(musicalKey)>MAX_MUSICAL_KEY_LENGTH):
				musicalKey=musicalKey[0:MAX_MUSICAL_KEY_LENGTH]
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
		#trackDb = Track.objects.get(title=title, artist=artist)
		# 1 find by artist and title
		trackList = Track.objects.filter(title=title, artist=artist)
		if(len(trackList) >0):
			trackDb=trackList[0]
			track = trackDb
			cptExistingTracks = cptExistingTracks+1
		else:
			#2 find by audio ID
			trackList = Track.objects.filter(audio_id=audio_id)
			if(len(trackList) >0):
				trackDb=trackList[0]
				track = trackDb
				track.title=title
				cptExistingTracks = cptExistingTracks+1
			#3 create it!
			else:
				track = Track()
				track.title=title
				cptNewTracks = cptNewTracks+1

		#update track infos
		#track.bpm=66 #FOR DEBUG AND PURGE
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
		track.audio_id=audio_id

		#print('About to save track with artist :', artist)
		track.save() #force save to add children

		#add this track to a temp list collection
		add_track_to_user_collection(userCollection, track)

	#print('xml parsing DONE!')
	return cptNewTracks, cptExistingTracks

	#traverseTree(xml.documentElement)

@login_required
def upload_file(request):
    if request.method == 'POST':
        form = UploadCollectionForm(request.POST, request.FILES)
        if form.is_valid():
        	#print('Form is valid!')
        	#get user
        	current_user = request.user
    		#print current_user.id
        	cptNewTracks, cptExistingTracks = handle_uploaded_file(request.FILES['file'], current_user)
        	#return HttpResponseRedirect('/admin/')
        	return render(request, 'track/import_collection.html', {'form': form, 'nb_new_tracks': cptNewTracks, 'nb_existing_tracks':cptExistingTracks, 'submitted':True})
    else:
        form = UploadCollectionForm()
    return render(request, 'track/import_collection.html', {'form': form})

def get_default_collection_for_user(currentUser):
	collectionList = Collection.objects.filter(user=currentUser)
	if (len(collectionList) <1): 
		#create new collection
		collection=Collection()
		collection.user=currentUser
		collection.name='User collection'
		collection.save()
	else:
		collection=collectionList[0]
	return collection

def add_track_to_user_collection(collection, track):
	existingTrack = collection.tracks.filter(title=track.title, artist=track.artist)
	if (existingTrack is None):
		collection.tracks.append(track)
		return True
	return False



