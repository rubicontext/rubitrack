"""
Tests d'import d'une collection Traktor (NML) : création des tracks,
extraction des cue points, dédoublonnage, playlists, collection utilisateur,
et rollback transactionnel en cas de fichier corrompu.
"""

from decimal import Decimal
from pathlib import Path

import pytest
from django.contrib.auth.models import User

from track.collection.import_collection import handle_uploaded_file
from track.models import Collection, CuePoint, Playlist, Track

FIXTURES = Path(__file__).parent / "fixtures"
TRAKTOR_NML = FIXTURES / "traktor_collection.nml"


@pytest.fixture
def user(db):
    return User.objects.create_user(username="dj", password="x")


@pytest.fixture
def imported(user):
    """Importe la fixture Traktor et retourne les compteurs."""
    new_count, existing_count = handle_uploaded_file(str(TRAKTOR_NML), user)
    return new_count, existing_count


@pytest.mark.django_db
class TestImportTracks:
    def test_creates_tracks_and_skips_samples(self, imported):
        new_count, existing_count = imported
        # 3 entrées valides, la 4e (sans INFO) est un sample ignoré
        assert new_count == 3
        assert existing_count == 0
        assert Track.objects.count() == 3
        assert not Track.objects.filter(title="Sample Kick").exists()

    def test_track_metadata(self, imported):
        strobe = Track.objects.get(title="Strobe")
        assert strobe.artist.name == "Deadmau5"
        assert float(strobe.bpm) == pytest.approx(128.0)
        assert strobe.ranking == 5  # RANKING=255
        assert strobe.playcount == 12
        assert strobe.file_path == "C:/:Users/:antoine/:Music/:strobe.mp3"
        assert strobe.audio_id == "AUDIOID_STROBE_001"

        opus = Track.objects.get(title="Opus - A#m - 6")
        assert opus.ranking == 4  # RANKING=204

    def test_tracks_added_to_user_collection(self, imported, user):
        collection = Collection.objects.get(user=user)
        assert collection.tracks.count() == 3

    def test_reimport_is_idempotent(self, imported, user):
        new_count, existing_count = handle_uploaded_file(str(TRAKTOR_NML), user)
        assert new_count == 0
        assert existing_count == 3
        assert Track.objects.count() == 3
        collection = Collection.objects.get(user=user)
        assert collection.tracks.count() == 3


@pytest.mark.django_db
class TestImportCuePoints:
    def test_cue_slots_mapping(self, imported):
        strobe = Track.objects.get(title="Strobe")
        by_slot = strobe.get_cue_points_by_slot()
        # Seuls les slots 1, 2, 5, 6 sont occupés
        assert set(by_slot) == {1, 2, 5, 6}
        # HOTCUE=0 (grid) -> slot 1
        assert by_slot[1].time_ms == Decimal("61.250000")
        assert by_slot[1].traktor_type == "4"
        # HOTCUE=1 -> slot 2 ; le doublon HOTCUE=1 est ignoré (first-wins)
        assert by_slot[2].time_ms == Decimal("30000.500000")
        # HOTCUE=4 (loop TYPE=5) -> slot 5 avec durée
        assert by_slot[5].len_ms == Decimal("15000.000000")
        assert by_slot[5].traktor_type == "5"
        # HOTCUE=5 (grid TYPE=4) -> slot 6
        assert by_slot[6].traktor_type == "4"

    def test_track_without_cues_has_no_cue_points(self, imported):
        track = Track.objects.get(title="No Cues Here")
        assert not track.cue_points.exists()

    def test_reimport_updates_cue_points_in_place(self, imported, user):
        strobe = Track.objects.get(title="Strobe")
        original_ids = {slot: cp.id for slot, cp in strobe.get_cue_points_by_slot().items()}
        handle_uploaded_file(str(TRAKTOR_NML), user)
        strobe.refresh_from_db()
        new_ids = {slot: cp.id for slot, cp in strobe.get_cue_points_by_slot().items()}
        assert new_ids == original_ids
        # Pas de CuePoint orphelins accumulés
        assert CuePoint.objects.count() == 5  # 4 Strobe + 1 Opus


@pytest.mark.django_db
class TestImportPlaylists:
    def test_playlist_created_with_tracks(self, imported):
        playlist = Playlist.objects.get(name="My Test Set")
        titles = {t.title for t in playlist.tracks.all()}
        assert titles == {"Strobe", "Opus - A#m - 6"}


@pytest.mark.django_db
class TestImportTransaction:
    def test_corrupt_file_rolls_back_everything(self, user, tmp_path):
        bad_xml = tmp_path / "bad.nml"
        bad_xml.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<NML VERSION="19">
  <COLLECTION ENTRIES="2">
    <ENTRY TITLE="Valid Track" ARTIST="Some Artist" AUDIO_ID="OK1">
      <LOCATION DIR="/:Music/:" FILE="ok.mp3" VOLUME="C:"></LOCATION>
      <INFO BITRATE="320000"></INFO>
    </ENTRY>
    <ENTRY TITLE="Broken Track" ARTIST="Some Artist" AUDIO_ID="KO2">
      <INFO BITRATE="320000"></INFO>
    </ENTRY>
  </COLLECTION>
  <PLAYLISTS></PLAYLISTS>
</NML>""",
            encoding="utf-8",
        )
        with pytest.raises(Exception):
            handle_uploaded_file(str(bad_xml), user)
        # Rollback complet : même la première entrée valide n'est pas persistée
        assert Track.objects.count() == 0
