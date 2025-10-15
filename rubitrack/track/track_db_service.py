from .models import Track, Artist, Transition, CurrentlyPlaying
from datetime import datetime
import pytz


def is_similar_with_char_diff(str1: str, str2: str, max_diff: int = 1) -> bool:
    """
    Check if two strings are similar with at most max_diff character differences.
    Handles cases like:
    - "le café" vs "le  café" (extra space)
    - "hello" vs "helo" (missing character)
    - "test" vs "tast" (different character)
    """
    if abs(len(str1) - len(str2)) > max_diff:
        return False
    
    # Use dynamic programming to calculate edit distance
    def edit_distance(s1, s2):
        m, n = len(s1), len(s2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        # Initialize first row and column
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
        
        # Fill the dp table
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1[i-1] == s2[j-1]:
                    dp[i][j] = dp[i-1][j-1]
                else:
                    dp[i][j] = 1 + min(
                        dp[i-1][j],    # deletion
                        dp[i][j-1],    # insertion
                        dp[i-1][j-1]   # substitution
                    )

        print("Edit distance between '{}' and '{}' is {}".format(s1, s2, dp[m][n]))

        return dp[m][n]
    
    return edit_distance(str1.lower().strip(), str2.lower().strip()) <= max_diff


def get_similar_tracks(track_title: str, artist_db: Artist, max_diff: int = 1):
    """
    Get all tracks by the same artist that are similar to the given title,
    with at most max_diff character differences.
    
    Args:
        track_title: The title to search for
        artist_db: The artist to search within
        max_diff: Maximum number of character differences allowed (default: 1)
    
    Returns:
        List of Track objects that are similar to the given title
    """
    similar_tracks = []
    all_tracks = Track.objects.filter(artist=artist_db)
    
    for track in all_tracks:
        if is_similar_with_char_diff(track_title, track.title, max_diff=max_diff):
            similar_tracks.append(track)
    
    return similar_tracks


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
    

    # happens with weird formatting in log file
    search_title = track_title[:-1]
    track_list = Track.objects.filter(title=search_title, artist=artist_db)
    if len(track_list) > 0:
        print("FOUND with 1 char removed :", search_title, " original:", track_title)
        return track_list[0]

    # check for close matches by same artists, when changing only 1 char is a match
    # like "le café" vs "le  café" (double space)
    all_tracks = Track.objects.filter(artist=artist_db)
    for track in all_tracks:
        if is_similar_with_char_diff(track_title, track.title, max_diff=1):
            print("FOUND with 1 char difference :", track.title, " original:", track_title)
            return track

    # no exact match found
    # check for close matches by same artists
    search_title = track_title.lstrip()
    track_list = Track.objects.filter(title__icontains=search_title, artist=artist_db)
    if len(track_list) > 0:
        print("FOUND with strip :", search_title, " original:", track_title)
        return track_list[0]
    
    # create new track, should only happen if no import of collection
    print("WARNING Created new track, :", track_title)
    track_db = Track()
    track_db.title = track_title
    track_db.artist = artist_db
    track_db.save()
    return track_db


def get_artist_db_from_artist_name(artist_name):
    """
    Get artist from database by name, with fallback strategies:
    1. Exact match (after trimming spaces)
    2. Exact match original (legacy)
    3. Case-insensitive match on trimmed
    4. Similar match with character differences
    5. icontains match
    6. Create new artist
    """
    if artist_name is None:
        return None
    original_name = artist_name
    artist_name = artist_name.strip()
    if not artist_name:
        artist_name = original_name  # fallback to original if becomes empty

    # Exact match on trimmed name
    artist_list = Artist.objects.filter(name=artist_name)
    if artist_list:
        return artist_list[0]

    # Exact match on original (just in case existing stored with trailing space)
    if original_name != artist_name:
        artist_list = Artist.objects.filter(name=original_name)
        if artist_list:
            return artist_list[0]

    # Case-insensitive exact match (handles different cases / accidental spaces)
    artist_list = Artist.objects.filter(name__iexact=artist_name)
    if artist_list:
        return artist_list[0]

    # Similar artist with small diff
    all_artists = Artist.objects.all()
    for artist in all_artists:
        if is_similar_with_char_diff(artist_name, artist.name.strip(), max_diff=1):
            print("FOUND similar artist with 1 char difference:", artist.name, "original:", original_name)
            return artist

    # icontains on trimmed
    artist_list = Artist.objects.filter(name__icontains=artist_name)
    if artist_list:
        print("FOUND with icontains:", artist_list[0].name, " original:", original_name)
        return artist_list[0]

    # icontains on original (rare case)
    if original_name != artist_name:
        artist_list = Artist.objects.filter(name__icontains=original_name)
        if artist_list:
            print("FOUND with icontains original:", artist_list[0].name, " original:", original_name)
            return artist_list[0]

    # Create new artist with trimmed canonical name
    artist_db = Artist()
    artist_db.name = artist_name
    artist_db.save()
    print("WARNING Created new artist (normalized from '{}'): {}".format(original_name, artist_name))
    return artist_db


def get_track_by_title_and_artist_name(track_title, artist_name):
    # Normalize whitespace on track title too
    normalized_title = track_title.strip() if track_title else track_title
    print("about to look for track:", normalized_title, "By artist :", artist_name)
    artist_db = get_artist_db_from_artist_name(artist_name)
    return get_track_db_from_title_artist(normalized_title, artist_db)


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
