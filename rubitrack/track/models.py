import datetime

from django.db import models
from django.utils import timezone

# Create your models here.

class Artist(models.Model):
    name = models.CharField(max_length=200)
    def __str__(self):
        return self.name

class Genre(models.Model):
    name = models.CharField(max_length=3)
    description = models.CharField(max_length=200)
    def __str__(self):
        return self.name

class Track(models.Model):
    title = models.CharField(max_length=200)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    genre = models.ForeignKey(Genre, on_delete=models.CASCADE, blank=True, null=True)
    date_catalog = models.DateTimeField('date added to catalog', auto_now_add=True, blank=True, null=True)
    bpm = models.FloatField(blank=True, null=True)
    #related_tracks = 
    #tostring :)    
    def __str__(self):
        return self.title + " - " +  self.artist.name
	#custom method
    def was_added_recently(self):
        if self.date_catalog:
            return self.date_catalog >= timezone.now() - datetime.timedelta(days=120)
        else:
            return False
    def is_techno(self):
        if self.genre:
            return self.genre.name.startswith('T')
        else:
            return False

class Playlist(models.Model):
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=200)
    tracks = models.ManyToManyField(Track)
    def __str__(self):
        return self.name

class TransitionType(models.Model):
    name = models.CharField(max_length=50)
    acronym = models.CharField(max_length=3)
    description = models.CharField(max_length=200)
    def __str__(self):
        return self.name

class TrackToTrack(models.Model):
    track_source = models.ForeignKey(Track, related_name="source", on_delete=models.CASCADE)
    track_destination = models.ForeignKey(Track, related_name="destination", on_delete=models.CASCADE)
    transition_type = models.ForeignKey(TransitionType, on_delete=models.CASCADE)
    comment = models.CharField(max_length=200)
    def __str__(self):
        return self.track_source.title + " - " +  self.track_destination.title


class CurrentlyPlaying(models.Model):
    date_played = models.DateTimeField('date played', auto_now_add=True, blank=True, null=True)
    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    def __str__(self):
        return self.track.title + " - " +  self.date_played