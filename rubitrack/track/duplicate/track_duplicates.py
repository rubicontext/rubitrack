

from track.models import Track


def find_duplicates():
    """experiment with finding duplicates"""

    all_corrupted_tracks = Track.objects.filter(bpm=None)

    for track in all_corrupted_tracks:
        print (track)




find_duplicates()
