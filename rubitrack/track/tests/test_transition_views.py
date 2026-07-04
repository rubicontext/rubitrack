"""
Tests des vues AJAX de transitions (add/delete/update), en POST + CSRF.
Régression: get_more_transition_block_history exigeait request.method=='GET' et
renvoyait un bloc VIDE sur les POST (delete/add/update) de la page history_editing
-> le bloc transitions disparaissait après suppression.
"""

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from track.models import Artist, Track, Transition, TransitionType


@pytest.fixture
def data(db):
    User.objects.create_superuser("admin", "a@a.fr", "x")
    artist = Artist.objects.create(name="DJ Test")
    cur = Track.objects.create(title="Current", artist=artist)
    other = Track.objects.create(title="Other", artist=artist)
    third = Track.objects.create(title="Third", artist=artist)
    mix = TransitionType.objects.create(name="Mix")
    t1 = Transition.objects.create(track_source=cur, track_destination=other,
                                   transition_type=mix, comment="A")
    t2 = Transition.objects.create(track_source=cur, track_destination=third,
                                   transition_type=mix, comment="B")
    client = Client()
    client.login(username="admin", password="x")
    return locals()


@pytest.mark.django_db
class TestTransitionViewsRequireePost:
    def test_delete_get_rejected(self, data):
        # GET sur une mutation -> 405 (protégé par @require_POST)
        assert data["client"].get(reverse("delete_transition_view")).status_code == 405

    def test_delete_history_returns_block_not_blank(self, data):
        """Régression: delete en contexte history renvoie le bloc peuplé, pas vide."""
        d = data
        resp = d["client"].post(reverse("delete_transition_view"), {
            "transitionDeleteId": d["t1"].id,
            "history": "true",
            "currentTrackId": d["cur"].id,
        })
        assert resp.status_code == 200
        html = resp.content.decode()
        assert "transitionsAllTable" in html          # bloc rendu (pas blank)
        assert "CUES" in html
        # t1 supprimée, t2 (vers Third) toujours présente dans le bloc
        assert not Transition.objects.filter(id=d["t1"].id).exists()
        assert "Third" in html

    def test_delete_currently_playing_context(self, data):
        """Contexte non-history: renvoie le bloc aussi (via get_more_transition_block)."""
        d = data
        resp = d["client"].post(reverse("delete_transition_view"), {
            "transitionDeleteId": d["t2"].id,
            "history": "false",
        })
        assert resp.status_code == 200

    def test_add_history_returns_block(self, data):
        d = data
        resp = d["client"].post(reverse("add_new_transition_view"), {
            "trackSourceId": d["cur"].id,
            "trackDestinationId": d["third"].id,
            "history": "true",
            "currentTrackId": d["cur"].id,
        })
        assert resp.status_code == 200
        assert "transitionsAllTable" in resp.content.decode()

    def test_update_comment_history(self, data):
        d = data
        resp = d["client"].post(reverse("update_transition_comment_view"), {
            "transitionUpdateId": d["t1"].id,
            "newComment": "commentaire modifié & spécial",
            "history": "true",
            "currentTrackId": d["cur"].id,
        })
        assert resp.status_code == 200
        d["t1"].refresh_from_db()
        assert d["t1"].comment == "commentaire modifié & spécial"
