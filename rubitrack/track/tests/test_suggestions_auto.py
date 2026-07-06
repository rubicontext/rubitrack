"""Tests des suggestions auto de la page Now Playing (get_list_track_suggestions_auto).

Régression: une track SANS genre (track.genre None) ou une Config avec un champ
None faisait planter la page principale (ValueError: Cannot use None as a query value).
"""

import pytest

from track.currently_playing.suggestions import get_list_track_suggestions_auto
from track.models import Artist, Config, Genre, Track


@pytest.mark.django_db
class TestSuggestionsAutoRobustness:
    def _cfg(self):
        cfg = Config.get_config()
        cfg.currently_bpm_range_suggestions = 6
        cfg.currently_musical_key_distance = 2
        cfg.currently_ranking_min = 1
        cfg.save()

    def test_track_without_genre_does_not_crash(self):
        self._cfg()
        a = Artist.objects.create(name="A")
        cur = Track.objects.create(title="Cur", artist=a, bpm=128, musical_key="Am")  # pas de genre
        Track.objects.create(title="Other", artist=a, bpm=129, musical_key="Am", ranking=5)
        result = get_list_track_suggestions_auto(cur)   # ne doit pas lever
        assert result is not None

    def test_with_genre_filters_on_comment(self):
        self._cfg()
        a = Artist.objects.create(name="A")
        g = Genre.objects.create(name="TEC")
        cur = Track.objects.create(title="Cur", artist=a, bpm=128, genre=g)
        Track.objects.create(title="Match", artist=a, bpm=128, ranking=5, comment="genre TEC ici")
        Track.objects.create(title="NoMatch", artist=a, bpm=128, ranking=5, comment="autre")
        titles = [t.title for t in get_list_track_suggestions_auto(cur)]
        assert "Match" in titles and "NoMatch" not in titles
