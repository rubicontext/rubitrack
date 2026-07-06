"""Tests PWA: manifest + service worker."""

import json

import pytest
from django.test import Client
from django.urls import reverse


@pytest.mark.django_db
class TestPwa:
    def test_manifest(self):
        resp = Client().get(reverse("pwa_manifest"))
        assert resp.status_code == 200
        assert "manifest" in resp["Content-Type"]
        data = json.loads(resp.content)
        assert data["start_url"] == reverse("currently_playing_view")
        assert data["display"] == "standalone"
        assert len(data["icons"]) >= 2
        assert any(i.get("purpose") == "maskable" for i in data["icons"])

    def test_service_worker(self):
        resp = Client().get(reverse("pwa_sw"))
        assert resp.status_code == 200
        assert "javascript" in resp["Content-Type"]
        assert resp["Service-Worker-Allowed"] == "/track/"
        body = resp.content.decode()
        assert "addEventListener('fetch'" in body
        assert reverse("currently_playing_view") in body
