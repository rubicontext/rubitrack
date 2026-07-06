"""Tests du Set Builder: page + API graphe (BFS forward sur les transitions)."""

import pytest
from django.urls import reverse

from track.models import Artist, Config, Track, Transition, TransitionType


@pytest.fixture
def graph_data(db):
    a = Artist.objects.create(name="A")
    tt = TransitionType.objects.create(name="Mix")
    t = {n: Track.objects.create(title=f"Node{n}", artist=a, bpm=128, musical_key="Am", ranking=4)
         for n in "ABCDEF"}

    def link(s, d, rk):
        Transition.objects.create(track_source=t[s], track_destination=t[d],
                                  transition_type=tt, ranking=rk)
    # A -> B(5), C(3) ; B -> D(4), E(2) ; C -> E(5) ; D -> F(5)
    link("A", "B", 5); link("A", "C", 3); link("B", "D", 4)
    link("B", "E", 2); link("C", "E", 5); link("D", "F", 5)
    return {"tracks": t, "tt": tt}


@pytest.mark.django_db
class TestSetBuilder:
    def test_page_ok(self, graph_data):
        from django.test import Client
        assert Client().get(reverse("set_builder")).status_code == 200

    def test_bfs_depths_and_edges(self, graph_data):
        from django.test import Client
        t = graph_data["tracks"]
        resp = Client().get(reverse("set_builder_graph", args=[t["A"].id]) + "?depth=3&branch=4")
        assert resp.status_code == 200
        data = resp.json()
        depth_by_id = {n["id"]: n["depth"] for n in data["nodes"]}
        assert depth_by_id[t["A"].id] == 0
        assert depth_by_id[t["B"].id] == 1 and depth_by_id[t["C"].id] == 1
        assert depth_by_id[t["F"].id] == 3
        # E atteint depuis B et C : présent une fois, mais les 2 arêtes existent
        e_targets = [(e["source"], e["target"]) for e in data["edges"]]
        assert (t["B"].id, t["E"].id) in e_targets
        assert (t["C"].id, t["E"].id) in e_targets

    def test_depth_limits_expansion(self, graph_data):
        from django.test import Client
        t = graph_data["tracks"]
        data = Client().get(reverse("set_builder_graph", args=[t["A"].id]) + "?depth=1").json()
        ids = {n["id"] for n in data["nodes"]}
        assert t["F"].id not in ids            # F est à profondeur 3
        assert data["depth"] == 1

    def test_branch_truncation_reported(self, graph_data):
        from django.test import Client
        t = graph_data["tracks"]
        # A a 2 sorties ; branch=1 -> 1 masquée
        data = Client().get(reverse("set_builder_graph", args=[t["A"].id]) + "?depth=1&branch=1").json()
        assert data["truncated"] >= 1

    def test_separator_excluded(self, graph_data):
        from django.test import Client
        t = graph_data["tracks"]
        Config._config_cache = None            # isolation: pas de cache résiduel
        cfg = Config.get_config()
        cfg.separator_track_id = t["C"].id     # C devient le séparateur
        cfg.save()                             # save() vide le cache de classe
        data = Client().get(reverse("set_builder_graph", args=[t["A"].id]) + "?depth=2").json()
        ids = {n["id"] for n in data["nodes"]}
        assert t["C"].id not in ids            # séparateur exclu des transitions

    def test_unknown_track_404(self, graph_data):
        from django.test import Client
        assert Client().get(reverse("set_builder_graph", args=[999999])).status_code == 404
