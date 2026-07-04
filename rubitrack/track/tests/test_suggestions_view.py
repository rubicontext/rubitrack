"""
Tests de ajax_suggestions — notamment le chemin "distance de clé < 12" qui
plantait (import erroné 'from rubitrack.track...' -> No module named rubitrack.track),
déclenché quand on bouge le slider de distance de clé sur history_editing.
"""

import json

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from track.models import Artist, Track


@pytest.fixture
def data(db):
    User.objects.create_superuser("admin", "a@a.fr", "x")
    artist = Artist.objects.create(name="DJ")
    cur = Track.objects.create(title="Current", artist=artist, bpm=128, musical_key="Am", ranking=5)
    # quelques voisines pour avoir des candidats
    Track.objects.create(title="N1", artist=artist, bpm=128, musical_key="Am", ranking=5)
    Track.objects.create(title="N2", artist=artist, bpm=129, musical_key="Em", ranking=4)
    client = Client()
    client.login(username="admin", password="x")
    return locals()


@pytest.mark.django_db
class TestAjaxSuggestions:
    def _post(self, client, **params):
        payload = {"track_id": None, "bpm_range": 5, "ranking_min": 1,
                   "musical_key_distance": 12, "genre_mode": "same"}
        payload.update(params)
        return client.post(reverse("ajax_suggestions"),
                           data=json.dumps(payload), content_type="application/json")

    def test_default_distance_ok(self, data):
        resp = self._post(data["client"], track_id=data["cur"].id, musical_key_distance=12)
        assert resp.status_code == 200
        assert "suggestions" in resp.json()

    def test_narrow_key_distance_no_crash(self, data):
        """Régression: distance < 12 déclenchait un import cassé -> 500."""
        resp = self._post(data["client"], track_id=data["cur"].id, musical_key_distance=4)
        assert resp.status_code == 200
        body = resp.json()
        assert "suggestions" in body and "count" in body

    def test_results_sorted_by_key_order(self, data):
        """Le tri par clé musicale nécessite MusicalKey peuplé (migration 0030)."""
        resp = self._post(data["client"], track_id=data["cur"].id, musical_key_distance=12)
        keys = [s.get("musical_key_order") for s in resp.json()["suggestions"]]
        # au moins une suggestion a un ordre non nul (MusicalKey peuplé)
        assert any(k is not None for k in keys)
