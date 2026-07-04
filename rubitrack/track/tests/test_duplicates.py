"""
Tests du système de gestion des doublons:
- détection à paliers (audio_id / titre-base / fuzzy) avec garde-fou durée
- règle absolue: cues des deux côtés -> cue_conflict, exclu de l'auto-merge
- mémoire persistante des candidats écartés
- merge sans perte (somme/max/coalesce, union des cues par slot, MergeLog)
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from track.duplicate.detection import (
    normalize_title_base, scan_duplicates, suggest_survivor,
)
from track.duplicate.manual_merge_duplicate import merge_duplicate_tracks
from track.models import (
    Artist, CuePoint, CurrentlyPlaying, DuplicateCandidate, MergeLog,
    Playlist, PlaylistTrack, Track, Transition, TransitionType, Collection,
)


class TestNormalizeTitleBase:
    def test_strips_key_and_rating(self):
        assert normalize_title_base("Back To Black - Gm - 5") == "back to black"
        assert normalize_title_base("Back To Black - A#m - 12") == "back to black"

    def test_keeps_mix_names(self):
        assert normalize_title_base("Opus (Extended Mix)") == "opus (extended mix)"
        # " - Original Mix" n'est pas un suffixe clé/note: conservé
        assert normalize_title_base("Song - Original Mix") == "song - original mix"

    def test_whitespace_and_case(self):
        assert normalize_title_base("  Strobe   Live ") == "strobe live"


@pytest.fixture
def dupe_data(db):
    artist = Artist.objects.create(name="Amy Winehouse")
    other_artist = Artist.objects.create(name="Amy Winehous")  # typo
    # T2: même artiste, même titre-base, clés/notes différentes
    t1 = Track.objects.create(title="Back To Black - Gm - 5", artist=artist, playtime=211, playcount=10)
    t2 = Track.objects.create(title="Back To Black - Am - 6", artist=artist, playtime=212, playcount=3)
    # T1: audio_id identique
    t3 = Track.objects.create(title="Rehab", artist=artist, audio_id="AUD-X", playtime=215)
    t4 = Track.objects.create(title="Rehab (copy)", artist=artist, audio_id="AUD-X", playtime=215)
    # T3 fuzzy: typo d'artiste
    t5 = Track.objects.create(title="Valerie", artist=artist, playtime=230)
    t6 = Track.objects.create(title="Valerie", artist=other_artist, playtime=231)
    # Garde-fou durée: même titre-base mais durées incompatibles
    t7 = Track.objects.create(title="Tears Dry - Am - 4", artist=artist, playtime=100)
    t8 = Track.objects.create(title="Tears Dry - Bm - 5", artist=artist, playtime=300)
    # Track sans rapport
    t9 = Track.objects.create(title="Completely Different Song", artist=artist, playtime=180)
    return locals()


@pytest.mark.django_db
class TestScan:
    def test_tiers_detected(self, dupe_data):
        stats = scan_duplicates()
        assert stats['created'] >= 3
        pairs = {
            (c.track_a_id, c.track_b_id): c
            for c in DuplicateCandidate.objects.all()
        }
        d = dupe_data
        # T1 audio_id -> 100
        c_audio = pairs[(d['t3'].id, d['t4'].id)]
        assert c_audio.score == 100
        assert 'same_audio_id' in c_audio.reasons
        # T2 titre-base -> >= 95
        c_base = pairs[(d['t1'].id, d['t2'].id)]
        assert c_base.score >= 95
        assert 'same_title_base' in c_base.reasons
        # T3 fuzzy cross-artiste
        c_fuzzy = pairs[(d['t5'].id, d['t6'].id)]
        assert c_fuzzy.score >= 90

    def test_duration_guard_blocks_pair(self, dupe_data):
        scan_duplicates()
        d = dupe_data
        assert not DuplicateCandidate.objects.filter(
            track_a=d['t7'], track_b=d['t8']).exists()

    def test_cue_conflict_flag(self, dupe_data):
        d = dupe_data
        CuePoint.objects.create(track=d['t1'], slot=1, time="0:30.000", time_ms=Decimal(30000))
        CuePoint.objects.create(track=d['t2'], slot=2, time="1:00.000", time_ms=Decimal(60000))
        scan_duplicates()
        candidate = DuplicateCandidate.objects.get(track_a=d['t1'], track_b=d['t2'])
        assert candidate.cue_conflict is True
        # audio pair sans cues: pas de conflit
        assert DuplicateCandidate.objects.get(track_a=d['t3'], track_b=d['t4']).cue_conflict is False

    def test_dismissed_memory_survives_rescan(self, dupe_data):
        scan_duplicates()
        d = dupe_data
        candidate = DuplicateCandidate.objects.get(track_a=d['t1'], track_b=d['t2'])
        candidate.status = DuplicateCandidate.STATUS_DISMISSED
        candidate.save()
        stats = scan_duplicates()
        candidate.refresh_from_db()
        assert candidate.status == DuplicateCandidate.STATUS_DISMISSED
        assert stats['skipped_memory'] >= 1


@pytest.mark.django_db
class TestSuggestSurvivor:
    def test_cues_win(self, dupe_data):
        d = dupe_data
        CuePoint.objects.create(track=d['t2'], slot=1, time="0:30.000", time_ms=Decimal(30000))
        assert suggest_survivor(d['t1'], d['t2']) == d['t2']

    def test_playcount_then_oldest(self, dupe_data):
        d = dupe_data
        assert suggest_survivor(d['t1'], d['t2']) == d['t1']  # playcount 10 > 3
        d['t2'].playcount = 10
        assert suggest_survivor(d['t1'], d['t2']) == d['t1']  # id plus ancien


@pytest.mark.django_db
class TestMerge:
    def test_full_merge_policy(self, dupe_data, django_user_model):
        d = dupe_data
        a, b = d['t1'], d['t2']
        a.ranking, b.ranking = 3, 5
        b.comment = "gros classique"
        now = timezone.now()
        a.date_last_played = now - timedelta(days=10)
        b.date_last_played = now
        a.save(), b.save()
        # cues: A slot 1, B slots 1 (conflit -> A gagne) et 5 (libre -> repris)
        CuePoint.objects.create(track=a, slot=1, time="0:30.000", time_ms=Decimal(30000))
        CuePoint.objects.create(track=b, slot=1, time="0:31.000", time_ms=Decimal(31000))
        cue_b5 = CuePoint.objects.create(track=b, slot=5, time="3:00.000", time_ms=Decimal(180000))
        # transitions de B
        mix = TransitionType.objects.create(name="Mix")
        Transition.objects.create(track_source=b, track_destination=d['t9'],
                                  transition_type=mix, ranking=4, comment="vers t9")
        # lecture en cours + playlist sur B
        CurrentlyPlaying.objects.create(track=b, date_played=now)
        user = django_user_model.objects.create_user("u")
        col = Collection.objects.create(user=user)
        playlist = Playlist.objects.create(name="Set", collection=col)
        PlaylistTrack.objects.create(playlist=playlist, track=b, position=0)

        merge_duplicate_tracks(a.id, b.id)
        a.refresh_from_db()

        assert not Track.objects.filter(id=b.id).exists()
        assert a.playcount == 13            # somme
        assert a.ranking == 5               # max
        assert a.date_last_played == now    # max
        assert a.comment == "gros classique"  # coalesce
        by_slot = a.get_cue_points_by_slot()
        assert set(by_slot) == {1, 5}
        assert by_slot[1].time == "0:30.000"       # A prioritaire sur slot en conflit
        assert by_slot[5].id == cue_b5.id          # slot libre comblé par B (id préservé)
        t = Transition.objects.get(track_source=a, track_destination=d['t9'])
        assert t.transition_type == mix and t.ranking == 4
        assert CurrentlyPlaying.objects.filter(track=a).count() == 1
        assert list(playlist.get_ordered_track_ids()) == [a.id]
        log = MergeLog.objects.get(deleted_track_id=b.id)
        assert log.survivor_id == a.id
        assert log.deleted_snapshot['title'] == "Back To Black - Am - 6"
        assert len(log.deleted_snapshot['cue_points']) == 2


@pytest.fixture
def admin_client_logged(client, db):
    User.objects.create_superuser(username="admin", password="x", email="a@a.fr")
    client.login(username="admin", password="x")
    return client


@pytest.mark.django_db
class TestAutoMergeRule:
    def test_cue_conflict_never_auto_merged(self, dupe_data, admin_client_logged):
        """LA règle: audio_id identique MAIS cues des deux côtés -> reste en manuel."""
        d = dupe_data
        # les deux paires certaines: t3/t4 (sans cues) et une nouvelle avec cues des 2 côtés
        t10 = Track.objects.create(title="Cued A", artist=d['artist'], audio_id="AUD-Y")
        t11 = Track.objects.create(title="Cued B", artist=d['artist'], audio_id="AUD-Y")
        CuePoint.objects.create(track=t10, slot=1, time="0:10.000", time_ms=Decimal(10000))
        CuePoint.objects.create(track=t11, slot=1, time="0:11.000", time_ms=Decimal(11000))
        scan_duplicates()

        response = admin_client_logged.post(reverse("auto_merge_certain"))
        assert response.status_code == 302
        # t3/t4 (score 100, pas de conflit) -> fusionnés
        assert Track.objects.filter(id__in=[d['t3'].id, d['t4'].id]).count() == 1
        # t10/t11 (score 100 MAIS conflit de cues) -> toujours 2 tracks, candidat pending
        assert Track.objects.filter(id__in=[t10.id, t11.id]).count() == 2
        candidate = DuplicateCandidate.objects.get(track_a=t10, track_b=t11)
        assert candidate.status == DuplicateCandidate.STATUS_PENDING
        assert candidate.cue_conflict is True
        # t1/t2 (titre-base, sans identité de fichier) -> jamais auto-mergés,
        # même si le score fuzzy post-normalisation atteint 100
        assert Track.objects.filter(id__in=[d['t1'].id, d['t2'].id]).count() == 2

    def test_dismiss_view(self, dupe_data, admin_client_logged):
        scan_duplicates()
        d = dupe_data
        candidate = DuplicateCandidate.objects.get(track_a=d['t1'], track_b=d['t2'])
        response = admin_client_logged.post(reverse("dismiss_candidate"),
                                            {"candidate_id": candidate.id})
        assert response.status_code == 302
        candidate.refresh_from_db()
        assert candidate.status == DuplicateCandidate.STATUS_DISMISSED

    def test_batch_page_shows_conflict_comparison(self, dupe_data, admin_client_logged):
        d = dupe_data
        CuePoint.objects.create(track=d['t1'], slot=1, time="0:30.000", time_ms=Decimal(30000))
        CuePoint.objects.create(track=d['t2'], slot=3, time="1:30.000", time_ms=Decimal(90000))
        scan_duplicates()
        response = admin_client_logged.get(reverse("manual_merge_track_batch"))
        content = response.content.decode()
        assert "CUES DES DEUX C" in content   # badge de la règle
        assert "0:30" in content and "1:30" in content  # comparaison des slots


@pytest.mark.django_db
class TestPrevention:
    def test_icecast_title_base_match_no_new_track(self, dupe_data):
        """Le log Icecast avec une clé/note différente ne crée plus de doublon."""
        from track.track_db_service import get_track_db_from_title_artist
        d = dupe_data
        found = get_track_db_from_title_artist("Back To Black - Cm - 3", d['artist'])
        assert found.id in (d['t1'].id, d['t2'].id)
        assert Track.objects.filter(title__startswith="Back To Black").count() == 2


@pytest.mark.django_db
class TestBulkArtistMerge:
    def test_groups_detected_with_survivor(self, admin_client_logged):
        from track.duplicate.display_duplicate import _artist_groups_with_survivor
        a1 = Artist.objects.create(name="Popof")
        a2 = Artist.objects.create(name="POPOF")
        a3 = Artist.objects.create(name="popof ")
        # a1 a le plus de tracks -> survivant
        for i in range(3):
            Track.objects.create(title=f"T{i}", artist=a1)
        Track.objects.create(title="U", artist=a2)
        groups = _artist_groups_with_survivor()
        popof = [g for g in groups if g['survivor'].name.strip().lower() == 'popof'][0]
        assert popof['survivor'].id == a1.id
        assert {a.id for a in popof['losers']} == {a2.id, a3.id}

    def test_bulk_merge_selected_groups(self, admin_client_logged):
        a1 = Artist.objects.create(name="Vitalic")
        a2 = Artist.objects.create(name="VITALIC")
        Track.objects.create(title="Poney", artist=a1)
        t2 = Track.objects.create(title="Birds", artist=a2)
        resp = admin_client_logged.post(reverse("merge_artist_groups"),
                                        {"survivor_ids": [a1.id]})
        assert resp.status_code == 302
        assert not Artist.objects.filter(id=a2.id).exists()   # loser supprimé
        t2.refresh_from_db()
        assert t2.artist_id == a1.id                          # track réaffectée

    def test_unchecked_group_not_merged(self, admin_client_logged):
        a1 = Artist.objects.create(name="Kavinsky")
        a2 = Artist.objects.create(name="KAVINSKY")
        Track.objects.create(title="Nightcall", artist=a1)
        # on ne coche pas ce groupe
        admin_client_logged.post(reverse("merge_artist_groups"), {"survivor_ids": []})
        assert Artist.objects.filter(id=a2.id).exists()       # intact
