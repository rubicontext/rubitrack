"""
Tests de la reconstruction des sets (historique de lecture) et de la
détection automatique des transitions récurrentes.
"""

from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from track.currently_playing.auto_transitions import detect_transitions_from_history
from track.currently_playing.set_history import build_sets
from track.models import Artist, Config, CurrentlyPlaying, Track, Transition


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
class TestAutoTransitions:
    def test_recurring_pair_created_once(self, history):
        d = history
        stats = detect_transitions_from_history()
        # A->B joué 2 fois -> créé ; B->C et A->B(set2)... B->C joué 1 fois -> non
        assert stats['created'] == 1
        transition = Transition.objects.get(track_source=d['a'], track_destination=d['b'])
        assert "Auto-détectée" in transition.comment
        assert "(x2)" in transition.comment

    def test_single_occurrence_not_created(self, history):
        d = history
        detect_transitions_from_history()
        assert not Transition.objects.filter(
            track_source=d['b'], track_destination=d['c']).exists()

    def test_separator_pairs_ignored(self, history):
        d = history
        detect_transitions_from_history()
        assert not Transition.objects.filter(track_source=d['sep']).exists()
        assert not Transition.objects.filter(track_destination=d['sep']).exists()

    def test_existing_transition_not_duplicated(self, history):
        d = history
        Transition.objects.create(track_source=d['a'], track_destination=d['b'],
                                  comment="ma transition manuelle", ranking=5)
        stats = detect_transitions_from_history()
        assert stats['created'] == 0
        assert stats['already_known'] == 1
        transition = Transition.objects.get(track_source=d['a'], track_destination=d['b'])
        assert transition.comment == "ma transition manuelle"  # pas écrasée

    def test_idempotent(self, history):
        detect_transitions_from_history()
        stats = detect_transitions_from_history()
        assert stats['created'] == 0
        assert Transition.objects.count() == 1

    def test_tools_view(self, history, client):
        User.objects.create_superuser(username="admin", password="x", email="a@a.fr")
        client.login(username="admin", password="x")
        response = client.post(reverse("detect_transitions"))
        assert response.status_code == 302
        assert Transition.objects.count() == 1
