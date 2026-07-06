"""Tests du UI Lab: page + compatibilité harmonique Camelot."""

import pytest
from django.test import Client
from django.urls import reverse

from track.models import Artist, Track, Transition, TransitionType
from track.ui_lab.ui_lab_view import _key_compat


class TestKeyCompat:
    def test_same_key_parfait(self):
        assert _key_compat("Am", "Am")["label"] == "Parfait"

    def test_relative_major_minor(self):
        # Am (8A) et C (8B) : même chiffre Camelot, lettre différente
        assert _key_compat("Am", "C")["label"] == "Relative"

    def test_adjacent_wheel(self):
        # Am (8A) -> Em (9A) : +1 sur la roue, même lettre
        assert _key_compat("Am", "Em")["label"] == "Adjacent"

    def test_energy_boost(self):
        # Am (8A) -> Bm (10A) : +2 = montée d'énergie
        assert _key_compat("Am", "Bm")["label"] == "Énergie +"

    def test_unknown_key(self):
        assert _key_compat("Am", None)["label"] == "?"
        assert _key_compat(None, None)["label"] == "?"


@pytest.mark.django_db
class TestUiLabPage:
    def test_page_renders_with_data(self):
        a = Artist.objects.create(name="A")
        tt = TransitionType.objects.create(name="Mix")
        cur = Track.objects.create(title="Cur", artist=a, bpm=128, musical_key="Am")
        from track.models import CuePoint
        CuePoint.objects.create(track=cur, slot=1, time="0:10")
        dest = Track.objects.create(title="Dst", artist=a, bpm=129, musical_key="Em")
        Transition.objects.create(track_source=cur, track_destination=dest,
                                  transition_type=tt, ranking=5)
        resp = Client().get(reverse("ui_lab"))
        assert resp.status_code == 200
        html = resp.content.decode()
        assert "ON AIR" in html and "DECK A" in html and "À SUIVRE" in html

    def test_page_no_data_graceful(self):
        resp = Client().get(reverse("ui_lab"))
        assert resp.status_code == 200
