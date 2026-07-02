"""
Tests de la vue d'import des clés musicales (elle référençait des templates
inexistants 'tool/...' au lieu de 'track/tools/...' et plantait en
TemplateDoesNotExist).
"""

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from track.musical_key.musical_key_models import MusicalKey


@pytest.fixture
def admin_client_logged(client, db):
    User.objects.create_superuser(username="admin", password="x", email="a@a.fr")
    client.login(username="admin", password="x")
    return client


@pytest.mark.django_db
def test_get_renders_form(admin_client_logged):
    response = admin_client_logged.get(reverse("import_musical_keys"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_post_imports_keys_and_renders_done(admin_client_logged):
    response = admin_client_logged.post(reverse("import_musical_keys"))
    assert response.status_code == 200
    # L'import doit avoir peuplé la table des clés musicales
    assert MusicalKey.objects.count() > 0
    assert MusicalKey.objects.filter(musical="Am").exists()
