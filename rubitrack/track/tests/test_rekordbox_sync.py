"""
Tests end-to-end de la synchronisation des cue points vers Rekordbox :
import de la fixture Traktor, puis injection des POSITION_MARK dans la
fixture rekordbox_collection.xml et vérification du XML produit.
"""

import logging
import xml.etree.ElementTree as ET
from decimal import Decimal
from pathlib import Path

import pytest
from django.contrib.auth.models import User

from track.collection.import_collection import handle_uploaded_file
from track.collection.rekordbox.synchronize_rekordbox_collection import (
    synchronize_rekordbox_collection,
)
from track.models import Artist, CuePoint, Track

FIXTURES = Path(__file__).parent / "fixtures"
TRAKTOR_NML = FIXTURES / "traktor_collection.nml"
REKORDBOX_XML = FIXTURES / "rekordbox_collection.xml"


@pytest.fixture
def populated_db(db):
    """Importe la collection Traktor puis ajoute une track avec cues manuels
    correspondant au TRACK 3 de la fixture Rekordbox."""
    user = User.objects.create_user(username="dj", password="x")
    handle_uploaded_file(str(TRAKTOR_NML), user)

    artist = Artist.objects.get(name="Deadmau5")
    manual = Track.objects.create(
        title="Manual Cues Track",
        artist=artist,
        file_path="C:/:Users/:antoine/:Music/:manual_cues.mp3",
    )
    # Slot 1 : pad 0 déjà occupé côté Rekordbox par un cue manuel -> doit être skippé en add_only
    CuePoint.objects.create(track=manual, slot=1, time="0:12.000", time_ms=Decimal("12000"), traktor_type="0")
    # Slot 2 : position à 45.45s, à moins de 100ms du cue manuel Rekordbox à 45.5s -> skippé en add_only
    CuePoint.objects.create(track=manual, slot=2, time="0:45.450", time_ms=Decimal("45450"), traktor_type="0")
    # Slot 8 : position libre -> ajouté
    CuePoint.objects.create(track=manual, slot=8, time="3:30.000", time_ms=Decimal("210000"), traktor_type="0")
    return user


def run_sync(tmp_path, mode):
    output = tmp_path / f"out_{mode}.xml"
    stats = synchronize_rekordbox_collection(str(REKORDBOX_XML), str(output), mode=mode)
    tree = ET.parse(output)
    return stats, tree


def get_track(tree, track_id):
    for track in tree.getroot().iter("TRACK"):
        if track.get("TrackID") == str(track_id):
            return track
    return None


def marks(track_element):
    return track_element.findall("POSITION_MARK")


@pytest.mark.django_db
class TestMatching:
    def test_match_by_artist_and_title(self, populated_db, tmp_path):
        stats, tree = run_sync(tmp_path, "overwrite")
        strobe = get_track(tree, 1)
        assert len(marks(strobe)) > 0

    def test_match_by_file_path_when_names_differ(self, populated_db, tmp_path):
        """TRACK 2 a un Name/Artist différent mais le même fichier que 'Opus'."""
        stats, tree = run_sync(tmp_path, "overwrite")
        opus = get_track(tree, 2)
        rcue_names = [m.get("Name") for m in marks(opus)]
        assert "RCue1" in rcue_names

    def test_unmatched_tracks_reported(self, populated_db, tmp_path):
        stats, tree = run_sync(tmp_path, "overwrite")
        unmatched_titles = {t["title"] for t in stats["unmatched_rekordbox_tracks"]}
        assert unmatched_titles == {"Not In Rubitrack"}

    def test_sampler_content_skipped(self, populated_db, tmp_path):
        stats, tree = run_sync(tmp_path, "overwrite")
        unmatched_titles = {t["title"] for t in stats["unmatched_rekordbox_tracks"]}
        assert "OneShot Kick" not in unmatched_titles

    def test_lookup_collision_logged_first_wins(self, populated_db, tmp_path, caplog):
        """Deux tracks Rubitrack qui se normalisent vers la même clé doivent
        déclencher un warning au lieu d'un écrasement silencieux."""
        artist = Artist.objects.get(name="Deadmau5")
        collider = Track.objects.create(title="Strobe (Club Mix)", artist=artist)
        CuePoint.objects.create(track=collider, slot=1, time="0:01.000", time_ms=Decimal("1000"))

        with caplog.at_level(logging.WARNING):
            stats, tree = run_sync(tmp_path, "overwrite")
        assert any("collision" in rec.message.lower() for rec in caplog.records)


@pytest.mark.django_db
class TestCuePointExport:
    def test_hot_cues_and_loops_overwrite(self, populated_db, tmp_path):
        stats, tree = run_sync(tmp_path, "overwrite")
        strobe = get_track(tree, 1)
        by_name = {m.get("Name"): m for m in marks(strobe)}

        # RCue1 : grid Traktor à 61.25ms -> hot cue pad 0
        assert by_name["RCue1"].get("Start") == "0.061"
        assert by_name["RCue1"].get("Type") == "0"
        assert by_name["RCue1"].get("Num") == "0"
        # RCue2 : hot cue pad 1 à 30.001s (30000.5 ms arrondi half-up)
        assert by_name["RCue2"].get("Start") == "30.001"
        assert by_name["RCue2"].get("Num") == "1"
        # RCue5 : loop 60s -> 75s (Type 4 avec End)
        assert by_name["RCue5"].get("Type") == "4"
        assert by_name["RCue5"].get("Start") == "60.000"
        assert by_name["RCue5"].get("End") == "75.000"
        # RCue6 : grid Traktor (TYPE=4) sur slot > 3 -> force_loop => Type 4 sans End
        assert by_name["RCue6"].get("Type") == "4"
        assert by_name["RCue6"].get("End") is None

    def test_overwrite_removes_all_existing_marks(self, populated_db, tmp_path):
        stats, tree = run_sync(tmp_path, "overwrite")
        manual = get_track(tree, 3)
        names = [m.get("Name") for m in marks(manual)]
        assert "My manual cue" not in names
        assert set(names) == {"RCue1", "RCue2", "RCue8"}

    def test_add_only_preserves_manual_cues(self, populated_db, tmp_path):
        stats, tree = run_sync(tmp_path, "add_only")
        manual = get_track(tree, 3)
        by_name = {m.get("Name"): m for m in marks(manual)}

        # Les cues manuels sont conservés
        assert "My manual cue" in by_name
        # RCue1 : pad 0 occupé par un cue manuel -> non ajouté
        assert "RCue1" not in by_name
        # RCue2 : à 45.45s, un cue manuel existe à 45.5s (< 100ms) -> non ajouté
        assert "RCue2" not in by_name
        # RCue8 : position libre -> ajouté
        assert "RCue8" in by_name
        # L'ancien RCue7 (généré par une sync précédente) a été nettoyé
        assert "RCue7" not in by_name

    def test_output_is_valid_xml_with_declaration(self, populated_db, tmp_path):
        stats, tree = run_sync(tmp_path, "overwrite")
        assert stats["success"] is True
        assert tree.getroot().tag == "DJ_PLAYLISTS"
