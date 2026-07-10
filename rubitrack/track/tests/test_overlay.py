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


@pytest.mark.django_db
class TestOverlay2:
    def test_sections_and_history(self, overlay_data):
        from django.utils import timezone as tz
        from datetime import timedelta
        d = overlay_data
        # historique: 2 tracks jouées avant la courante
        CurrentlyPlaying.objects.create(track=d["d1"], date_played=tz.now() - timedelta(minutes=20))
        CurrentlyPlaying.objects.create(track=d["d2"], date_played=tz.now() - timedelta(minutes=10))
        resp = d["client"].get(reverse("overlay2"))
        assert resp.status_code == 200
        html = resp.content.decode()
        assert 'data-sec="transitions"' in html      # section repliable transitions
        assert 'data-sec="history"' in html          # section repliable historique
        assert "DERNIÈRES JOUÉES" in html
        assert "Next Two" in html                    # dans l'historique
        assert "ov-content" in html                  # squelette avec JS

    def test_partial_fragment(self, overlay_data):
        resp = overlay_data["client"].get(reverse("overlay2") + "?partial=1")
        html = resp.content.decode()
        assert 'data-sec="transitions"' in html
        assert "ov-content" not in html              # fragment sans squelette

    def test_current_track_excluded_from_history(self, overlay_data):
        d = overlay_data
        html = d["client"].get(reverse("overlay2")).content.decode()
        # la track en cours ne doit pas apparaître dans DERNIÈRES JOUÉES
        history_part = html.split("DERNIÈRES JOUÉES")[1]
        assert "Playing Now" not in history_part

    def test_add_button_or_check_on_history(self, overlay_data):
        from datetime import timedelta
        from django.utils import timezone as tz
        d = overlay_data
        # d1 a déjà une transition d1->cur ; d2 non
        Transition.objects.create(track_source=d["d1"], track_destination=d["cur"],
                                  transition_type=d["mix"], ranking=3)
        CurrentlyPlaying.objects.create(track=d["d1"], date_played=tz.now() - timedelta(minutes=20))
        CurrentlyPlaying.objects.create(track=d["d2"], date_played=tz.now() - timedelta(minutes=10))
        html = d["client"].get(reverse("overlay2")).content.decode()
        history_part = html.split("DERNIÈRES JOUÉES")[1]
        assert "ov-addbtn" in history_part           # bouton + présent (d2)
        assert "ov-added" in history_part            # coche ✓ présente (d1)


@pytest.mark.django_db
class TestOverlayAddTransition:
    def test_creates_with_comment(self, overlay_data):
        d = overlay_data
        d3 = Track.objects.create(title="Fresh", artist=d["artist"], bpm=126)
        resp = d["client"].post(reverse("overlay_add_transition"), {
            "source_id": d3.id, "destination_id": d["cur"].id, "comment": "5:1 6Cut",
        })
        assert resp.status_code == 200
        assert resp.json() == {"ok": True, "created": True}
        transition = Transition.objects.get(track_source=d3, track_destination=d["cur"])
        assert transition.comment == "5:1 6Cut"

    def test_existing_updates_comment(self, overlay_data):
        d = overlay_data
        # d1->cur existe déjà (créée dans overlay_data avec play_count=5)
        resp = d["client"].post(reverse("overlay_add_transition"), {
            "source_id": d["cur"].id, "destination_id": d["d1"].id, "comment": "nouveau com",
        })
        assert resp.json()["created"] is False
        t = Transition.objects.get(track_source=d["cur"], track_destination=d["d1"])
        assert t.comment == "nouveau com"
        # pas de doublon créé
        assert Transition.objects.filter(track_source=d["cur"],
                                         track_destination=d["d1"]).count() == 1

    def test_same_track_rejected(self, overlay_data):
        d = overlay_data
        resp = d["client"].post(reverse("overlay_add_transition"), {
            "source_id": d["cur"].id, "destination_id": d["cur"].id, "comment": "",
        })
        assert resp.status_code == 400

    def test_get_rejected(self, overlay_data):
        assert overlay_data["client"].get(reverse("overlay_add_transition")).status_code == 405

    def test_unknown_track_404(self, overlay_data):
        d = overlay_data
        resp = d["client"].post(reverse("overlay_add_transition"), {
            "source_id": 999999, "destination_id": d["cur"].id, "comment": "",
        })
        assert resp.status_code == 404
