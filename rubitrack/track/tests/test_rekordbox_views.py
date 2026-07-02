"""
Tests de l'API de synchronisation Rekordbox : contrat ZIP + header X-Sync-Stats,
validations d'entrée (fichier manquant, extension, taille, root XML).
"""

import io
import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from track.models import Config

FIXTURES = Path(__file__).parent / "fixtures"
REKORDBOX_XML = FIXTURES / "rekordbox_collection.xml"


@pytest.fixture
def admin_client_logged(client, db):
    User.objects.create_superuser(username="admin", password="x", email="a@a.fr")
    client.login(username="admin", password="x")
    return client


@pytest.fixture
def sync_url():
    return reverse("rekordbox_api_synchronize")


@pytest.mark.django_db
class TestSynchronizeApi:
    def test_missing_file_returns_400(self, admin_client_logged, sync_url):
        response = admin_client_logged.post(sync_url, {})
        assert response.status_code == 400
        assert "Aucun fichier" in response.json()["error"]

    def test_non_xml_file_returns_400(self, admin_client_logged, sync_url):
        upload = io.BytesIO(b"whatever")
        upload.name = "collection.txt"
        response = admin_client_logged.post(sync_url, {"rekordbox_file": upload})
        assert response.status_code == 400
        assert "XML" in response.json()["error"]

    def test_oversized_file_returns_413(self, admin_client_logged, sync_url):
        config = Config.get_config()
        config.max_upload_size_mb = 0
        config.save()

        upload = io.BytesIO(b"<DJ_PLAYLISTS></DJ_PLAYLISTS>")
        upload.name = "collection.xml"
        response = admin_client_logged.post(sync_url, {"rekordbox_file": upload})
        assert response.status_code == 413
        assert "volumineux" in response.json()["error"]

    def test_invalid_root_returns_400(self, admin_client_logged, sync_url):
        upload = io.BytesIO(b'<?xml version="1.0"?><NML VERSION="19"></NML>')
        upload.name = "collection.xml"
        response = admin_client_logged.post(sync_url, {"rekordbox_file": upload})
        assert response.status_code == 400
        assert "DJ_PLAYLISTS" in response.json()["error"]

    def test_valid_file_returns_zip_with_stats_header(self, admin_client_logged, sync_url):
        with open(REKORDBOX_XML, "rb") as f:
            response = admin_client_logged.post(
                sync_url, {"rekordbox_file": f, "mode": "overwrite"}
            )

        assert response.status_code == 200
        assert response["Content-Type"] == "application/zip"
        assert 'attachment; filename="rekordbox_sync_' in response["Content-Disposition"]

        stats = json.loads(response["X-Sync-Stats"])
        assert stats["mode"] == "overwrite"
        # 5 TRACK dans la fixture; base vide donc aucune matchée,
        # le sampler est exclu du décompte des non-trouvées
        assert stats["total_tracks_in_rekordbox_file"] == 5
        assert stats["tracks_found_and_matched"] == 0
        assert stats["unmatched_count"] == 4

        # Le ZIP contient le XML modifié (root DJ_PLAYLISTS) + la liste des non-trouvées
        zf = zipfile.ZipFile(io.BytesIO(response.content))
        names = zf.namelist()
        assert len(names) == 2
        xml_name = next(n for n in names if n.endswith(".xml"))
        txt_name = next(n for n in names if n.endswith(".txt"))
        root = ET.fromstring(zf.read(xml_name))
        assert root.tag == "DJ_PLAYLISTS"
        not_found = zf.read(txt_name).decode("utf-8")
        assert "Not In Rubitrack" in not_found

    def test_requires_staff(self, client, db, sync_url):
        response = client.post(sync_url, {})
        # Redirection vers la page de login admin
        assert response.status_code == 302


@pytest.mark.django_db
class TestStatsApi:
    def test_stats_endpoint(self, admin_client_logged):
        response = admin_client_logged.get(reverse("rekordbox_api_stats"))
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["stats"]["total_tracks"] == 0
