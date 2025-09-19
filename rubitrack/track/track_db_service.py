from .models import Track, Artist, Transition, CurrentlyPlaying
from datetime import datetime
import pytz


def are_track_related(track_source, track_destination):
    transition_list = Transition.objects.filter(track_source=track_source, track_destination=track_destination)
    if len(transition_list) > 0:
        return True
    return False


def get_track_related_text(track_source, track_destination):
    transition_list = Transition.objects.filter(track_source=track_source, track_destination=track_destination)
    if len(transition_list) > 0:
        return transition_list[0].comment
    return None


def get_track_db_from_title_artist(track_title: str, artist_db: Artist):
    track_list = Track.objects.filter(title=track_title, artist=artist_db)
    if len(track_list) == 1:
        return track_list[0]

    if len(track_list) > 1:
        print("WARNING DUPLICATE track :", track_title, "By artist :", artist_db.name)
        return track_list[0]

    # no exact match found
    # check for close matches by same artists
    search_title = track_title.lstrip()
    track_list = Track.objects.filter(title__icontains=search_title, artist=artist_db)
    if len(track_list) > 0:
        print("FOUND with strip")
        return track_list[0]

    # happens with weird formatting in log file
    search_title = track_title[:-1]
    track_list = Track.objects.filter(title__icontains=search_title, artist=artist_db)
    if len(track_list) > 0:
        print("FOUND with 1 char removed")
        return track_list[0]

    # create new track, should only happen if no import of collection
    print("WARNING Created new track, :", track_title)
    track_db = Track()
    track_db.title = track_title
    track_db.artist = artist_db
    track_db.save()
    return track_db


def get_track_by_title_and_artist_name(track_title, artist_name):
    print("about to look for track:", track_title, "By artist :", artist_name)
    artist_list = Artist.objects.filter(name=artist_name)
    # create artist if needed
    if len(artist_list) < 1:
        # check for close matches by same artists
        artist_list = Artist.objects.filter(name__icontains=artist_name)
        if len(artist_list) > 0:
            artist_db = artist_list[0]
        else:
            artist_db = Artist()
            artist_db.name = artist_name
            artist_db.save()
            print("WARNING Created new artist:", artist_name)
    else:
        artist_db = artist_list[0]

    return get_track_db_from_title_artist(track_title, artist_db)


def get_currently_playing_track_from_db():
    current_playlist = CurrentlyPlaying.objects.order_by('date_played')
    if len(current_playlist) > 0:
        current_track = current_playlist[len(current_playlist) - 1].track
        return current_track
    else:
        return None


def get_currently_playing_track_time_from_db():
    current_playlist = CurrentlyPlaying.objects.order_by('date_played')
    if len(current_playlist) > 0:
        current_track_time = current_playlist[len(current_playlist) - 1].date_played
        return current_track_time
    else:
        return None
