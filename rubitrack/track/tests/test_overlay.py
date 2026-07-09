"""Tests de la mini-vue overlay (par-dessus Traktor)."""

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from track.models import Artist, CurrentlyPlaying, Track, Transition, TransitionType


@pytest.fixture
def overlay_data(db):
    User.objects.create_superuser("admin", "a@a.fr", "x")
    artist = Artist.objects.create(name="DJ")
    cur = Track.objects.create(title="Playing Now", artist=artist, bpm=128, musical_key="Am")
    d1 = Track.objects.create(title="Next One", artist=artist, bpm=129, musical_key="Em")
    d2 = Track.objects.create(title="Next Two", artist=artist, bpm=127, musical_key="Am")
    mix = TransitionType.objects.create(name="Mix")
    # d2 mieux notée mais d1 plus JOUÉE -> d1 doit sortir en premier
    Transition.objects.create(track_source=cur, track_destination=d1,
                              transition_type=mix, ranking=3, play_count=5)
    Transition.objects.create(track_source=cur, track_destination=d2,
                              transition_type=mix, ranking=5, play_count=0)
    CurrentlyPlaying.objects.create(track=cur, date_played=timezone.now())
    client = Client()
    client.login(username="admin", password="x")
    return locals()


@pytest.mark.django_db
class TestOverlay:
    def test_requires_login(self, db):
        resp = Client().get(reverse("overlay"))
        assert resp.status_code == 302 and "login" in resp.url

    def test_full_page(self, overlay_data):
        resp = overlay_data["client"].get(reverse("overlay"))
        assert resp.status_code == 200
        html = resp.content.decode()
        assert "Playing Now" in html
        assert "ov-content" in html          # page complète (avec JS refresh)

    def test_partial_no_wrapper(self, overlay_data):
        resp = overlay_data["client"].get(reverse("overlay") + "?partial=1")
        html = resp.content.decode()
        assert "Playing Now" in html
        assert "ov-content" not in html      # fragment seul, sans le squelette

    def test_next_sorted_by_play_count(self, overlay_data):
        html = overlay_data["client"].get(reverse("overlay")).content.decode()
        # d1 (jouée 5x, note 3) doit apparaître avant d2 (jouée 0x, note 5)
        assert html.index("Next One") < html.index("Next Two")
        assert "▶5" in html

    def test_no_current_track_graceful(self, db):
        User.objects.create_superuser("admin2", "a@a.fr", "x")
        client = Client()
        client.login(username="admin2", password="x")
        resp = client.get(reverse("overlay"))
        assert resp.status_code == 200
        assert "Pas de lecture en cours" in resp.content.decode()
