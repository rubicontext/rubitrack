import datetime

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

# Create your models here.
Ranking_CHOICES = ((1, 'Poor'), (2, 'Average'), (3, 'Good'), (4, 'Very Good'), (5, 'Excellent'))


class Artist(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Genre(models.Model):
    name = models.CharField(max_length=3)
    description = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return self.name


class Track(models.Model):
    title = models.CharField(max_length=200)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    genre = models.ForeignKey(Genre, on_delete=models.CASCADE, blank=True, null=True)
    bpm = models.FloatField(blank=True, null=True)
    ranking = models.IntegerField(choices=Ranking_CHOICES, default=None, blank=True, null=True)
    musical_key = models.CharField(max_length=3, blank=True, null=True)
    file_name = models.CharField(max_length=200, blank=True, null=True)
    comment = models.CharField(max_length=500, blank=True, null=True)
    comment2 = models.CharField(max_length=500, blank=True, null=True)
    position = models.PositiveIntegerField(default=0, blank=False, null=False)
    bitrate = models.IntegerField(blank=True, null=True)
    playcount = models.IntegerField(blank=True, null=True)
    energy = models.IntegerField(blank=True, null=True)
    audio_id = models.CharField(max_length=2000, blank=True, null=True)
    location_dir = models.CharField(max_length=2000, blank=True, null=True)
    file_path = models.CharField(max_length=2000, blank=True, null=True)

    # all dates
    date_collection_created = models.DateTimeField('date added to collection', auto_now_add=True, blank=True, null=True)
    date_collection_updated = models.DateTimeField(
        'date of modification in collection', auto_now_add=True, blank=True, null=True
    )
    date_collection_source_updated = models.DateTimeField(
        'date of modification in the source collection (Traktor/Serato/Rekordbox)',
        auto_now_add=True,
        blank=True,
        null=True,
    )
    date_last_played = models.DateTimeField('date last played', blank=True, null=True)

    class Meta(object):
        ordering = ['position']

    # related_tracks =
    # tostring :)
    def __str__(self):
        return self.title + " - " + self.artist.name

    # custom method
    def was_added_recently(self):
        if self.date_collection_created:
            return self.date_collection_created >= timezone.now() - datetime.timedelta(days=120)
        else:
            return False

    def is_techno(self):
        if self.genre:
            return self.genre.name.startswith('T')
        else:
            return False


class Playlist(models.Model):
    name = models.CharField(max_length=200)
    track_ids = models.CharField(max_length=20000, blank=True, null=True)
    tracks = models.ManyToManyField(Track)
    rank = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return self.name


class Collection(models.Model):
    name = models.CharField(max_length=200)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    tracks = models.ManyToManyField(Track)

    def __str__(self):
        return self.name


class TransitionType(models.Model):
    name = models.CharField(max_length=50)
    acronym = models.CharField(max_length=3, blank=True, null=True)
    description = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return self.name


class Transition(models.Model):
    track_source = models.ForeignKey(Track, related_name="source", on_delete=models.CASCADE)
    track_destination = models.ForeignKey(Track, related_name="destination", on_delete=models.CASCADE)
    transition_type = models.ForeignKey(TransitionType, on_delete=models.CASCADE, null=True)
    ranking = models.IntegerField(choices=Ranking_CHOICES, default=3)
    comment = models.TextField(max_length=200, blank=True, null=True)
    # used for sortable admin
    position = models.PositiveIntegerField(default=0, blank=False, null=False)

    class Meta(object):
        ordering = ['position']

    def __str__(self):
        return self.track_source.title + " - " + self.track_destination.title


class CurrentlyPlaying(models.Model):
    date_played = models.DateTimeField('date played', blank=True, null=True)
    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    related_to_current_track = False
    related_to_current_track_text = ''

    def __str__(self):
        return self.track.title + " - " + self.date_played.strftime("%H:%M:%S, %d/%m/%Y")
