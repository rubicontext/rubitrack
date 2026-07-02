"""
Vérifie que la protection CSRF est active sur les vues POST sensibles
(elles étaient historiquement en @csrf_exempt alors que tous les templates
appelants envoient déjà le token).
"""

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse


@pytest.fixture
def csrf_client(db):
    """Client connecté qui applique la vérification CSRF (désactivée par défaut en test)."""
    User.objects.create_superuser(username="admin", password="x", email="a@a.fr")
    client = Client(enforce_csrf_checks=True)
    client.login(username="admin", password="x")
    return client


@pytest.mark.django_db
@pytest.mark.parametrize(
    "url_name",
    ["ajax_suggestions", "manual_merge_track", "manual_merge_artist"],
)
def test_post_without_csrf_token_is_rejected(csrf_client, url_name):
    response = csrf_client.post(reverse(url_name), {})
    assert response.status_code == 403
