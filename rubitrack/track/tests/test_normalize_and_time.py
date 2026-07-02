"""
Tests unitaires purs (sans DB) : normalisation de textes et conversions de temps
du synchronizer Rekordbox.
"""

from decimal import Decimal

import pytest

from track.collection.rekordbox.synchronize_rekordbox_collection import (
    RekordboxCollectionSynchronizer,
)


@pytest.fixture
def sync():
    return RekordboxCollectionSynchronizer()


class TestNormalizeText:
    def test_strips_key_and_rating_suffix(self, sync):
        assert sync._normalize_text("Strobe - Am - 6") == "Strobe"

    def test_strips_rating_only_suffix(self, sync):
        assert sync._normalize_text("Strobe - 6") == "Strobe"

    def test_removes_parenthetical_content(self, sync):
        assert sync._normalize_text("Strobe (Original Mix)") == "Strobe"

    def test_removes_watermark_tokens(self, sync):
        assert sync._normalize_text("Strobe my-free-mp3s.com") == "Strobe"
        assert sync._normalize_text("Strobe FREE DOWNLOAD") == "Strobe"

    def test_collapses_whitespace(self, sync):
        assert sync._normalize_text("  Strobe   Club  Edit ") == "Strobe Club Edit"

    def test_none_and_empty(self, sync):
        assert sync._normalize_text("") == ""
        assert sync._normalize_text(None) == ""


class TestParseTimeToSeconds:
    def test_mm_ss_format(self, sync):
        assert sync.parse_time_to_seconds("1:05") == 65.0

    def test_raw_milliseconds(self, sync):
        assert sync.parse_time_to_seconds("29801.179384") == pytest.approx(29.801179384)

    def test_seconds_value(self, sync):
        assert sync.parse_time_to_seconds("29.801") == pytest.approx(29.801)

    def test_numeric_input(self, sync):
        assert sync.parse_time_to_seconds(65000) == 65.0
        assert sync.parse_time_to_seconds(42.5) == 42.5

    def test_invalid_returns_zero(self, sync):
        assert sync.parse_time_to_seconds("not a time") == 0.0


class TestSecondsToRekordboxPosition:
    def test_integer_seconds(self, sync):
        assert sync.seconds_to_rekordbox_position(33) == "33.000"

    def test_rounding_half_up(self, sync):
        assert sync.seconds_to_rekordbox_position(Decimal("1.0005")) == "1.001"

    def test_float_precision(self, sync):
        assert sync.seconds_to_rekordbox_position(29.801179384) == "29.801"


class TestNormalizePaths:
    def test_traktor_path_normalization(self, sync):
        assert (
            sync._normalize_traktor_path("C:/:Users/:antoine/:Music/:strobe.mp3")
            == "c:/users/antoine/music/strobe.mp3"
        )

    def test_rekordbox_location_normalization(self, sync):
        assert (
            sync._normalize_rekordbox_location(
                "file://localhost/C:/Users/antoine/Music/strobe.mp3"
            )
            == "c:/users/antoine/music/strobe.mp3"
        )

    def test_rekordbox_location_url_encoded(self, sync):
        assert (
            sync._normalize_rekordbox_location(
                "file://localhost/C:/Program%20Files/Pioneer/rekordbox/Sampler/kick.wav"
            )
            == "c:/program files/pioneer/rekordbox/sampler/kick.wav"
        )

    def test_empty_values(self, sync):
        assert sync._normalize_traktor_path("") == ""
        assert sync._normalize_rekordbox_location("") == ""
