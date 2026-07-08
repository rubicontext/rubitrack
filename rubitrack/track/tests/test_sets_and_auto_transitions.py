"""
Tests de la reconstruction des sets (historique de lecture) et des
transitions candidates (PROPOSITIONS, jamais de création auto).
"""

from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from track.currently_playing.auto_transitions import find_transition_candidates_from_history
from track.currently_playing.set_history import build_sets
from track.models import Artist, Config, CurrentlyPlaying, Track, Transition, TransitionType


@pytest.fixture
def history(db):
    """Deux sets distincts + un enchaînement récurrent A->B (joué 2 fois)."""
    artist = Artist.objects.create(name="DJ Test")
    a = Track.objects.create(title="Alpha", artist=artist, bpm=124)
    b = Track.objects.create(title="Bravo", artist=artist, bpm=126)
    c = Track.objects.create(title="Charlie", artist=artist, bpm=128)
    sep = Track.objects.create(title="=== SEPARATOR ===", artist=artist)
    config = Config.get_config()
    config.separator_track_id = sep.id
    config.save()

    base = timezone.now() - timedelta(days=1)
    # Set 1: A -> B -> C (espacés de 5 min)
    for i, t in enumerate((a, b, c)):
        CurrentlyPlaying.objects.create(track=t, date_played=base + timedelta(minutes=5 * i))
    # Grosse pause (2 h) puis Set 2: A -> B -> séparateur -> C
    start2 = base + timedelta(hours=2)
    CurrentlyPlaying.objects.create(track=a, date_played=start2)
    CurrentlyPlaying.objects.create(track=b, date_played=start2 + timedelta(minutes=4))
    CurrentlyPlaying.objects.create(track=sep, date_played=start2 + timedelta(minutes=8))
    CurrentlyPlaying.objects.create(track=c, date_played=start2 + timedelta(minutes=12))
    return locals()


@pytest.mark.django_db
class TestBuildSets:
    def test_two_sets_reconstructed(self, history):
        sets = build_sets()
        assert len(sets) == 2
        # Le plus récent d'abord
        assert sets[0]['start'] > sets[1]['start']
        assert len(sets[1]['plays']) == 3      # set 1: A, B, C
        assert len(sets[0]['plays']) == 3      # set 2: A, B, C (séparateur exclu)

    def test_separator_excluded(self, history):
        sets = build_sets()
        titles = [p.track.title for s in sets for p in s['plays']]
        assert "=== SEPARATOR ===" not in titles

    def test_tracklist_text_format(self, history):
        sets = build_sets()
        lines = sets[1]['tracklist_text'].splitlines()
        assert lines[0] == "01. DJ Test - Alpha"
        assert lines[2] == "03. DJ Test - Charlie"

    def test_avg_bpm(self, history):
        sets = build_sets()
        assert sets[1]['avg_bpm'] == pytest.approx(126.0)

    def test_sets_page(self, history, client):
        User.objects.create_superuser(username="admin", password="x", email="a@a.fr")
        client.login(username="admin", password="x")
        response = client.get(reverse("sets_view"))
        content = response.content.decode()
        assert response.status_code == 200
        assert "01. DJ Test - Alpha" in content
        assert "Copier la tracklist" in content


@pytest.mark.django_db
class TestTransitionCandidates:
    """Propositions uniquement: le finder ne crée RIEN, la création est au clic."""

    def test_recurring_pair_is_candidate_no_creation(self, history):
        d = history
        candidates = find_transition_candidates_from_history()
        pairs = {(c['source_id'], c['destination_id']): c['occurrences'] for c in candidates}
        assert pairs.get((d['a'].id, d['b'].id)) == 2      # A->B joué 2 fois -> candidat
        assert Transition.objects.count() == 0             # RIEN créé automatiquement

    def test_single_occurrence_excluded(self, history):
        d = history
        pairs = {(c['source_id'], c['destination_id'])
                 for c in find_transition_candidates_from_history()}
        assert (d['b'].id, d['c'].id) not in pairs         # B->C joué 1 fois

    def test_separator_pairs_excluded(self, history):
        d = history
        candidates = find_transition_candidates_from_history()
        ids = {c['source_id'] for c in candidates} | {c['destination_id'] for c in candidates}
        assert d['sep'].id not in ids

    def test_existing_transition_not_proposed(self, history):
        d = history
        Transition.objects.create(track_source=d['a'], track_destination=d['b'], ranking=5)
        pairs = {(c['source_id'], c['destination_id'])
                 for c in find_transition_candidates_from_history()}
        assert (d['a'].id, d['b'].id) not in pairs

    def test_page_lists_candidates(self, history, client):
        User.objects.create_superuser(username="admin", password="x", email="a@a.fr")
        client.login(username="admin", password="x")
        response = client.get(reverse("set_transitions"))
        assert response.status_code == 200
        assert "Alpha" in response.content.decode()

    def test_creation_only_on_click(self, history, client):
        d = history
        TransitionType.objects.get_or_create(id=1, defaults={'name': 'Mix'})
        User.objects.create_superuser(username="admin", password="x", email="a@a.fr")
        client.login(username="admin", password="x")
        # afficher la page ne crée rien
        client.get(reverse("set_transitions"))
        assert Transition.objects.count() == 0
        # clic "Ajouter" (POST) -> crée exactement une transition
        response = client.post(reverse("add_set_transition"),
                               {"source_id": d['a'].id, "destination_id": d['b'].id})
        assert response.status_code == 302
        assert Transition.objects.filter(
            track_source=d['a'], track_destination=d['b']).count() == 1

    def test_add_get_rejected(self, history, client):
        User.objects.create_superuser(username="admin", password="x", email="a@a.fr")
        client.login(username="admin", password="x")
        assert client.get(reverse("add_set_transition")).status_code == 405
