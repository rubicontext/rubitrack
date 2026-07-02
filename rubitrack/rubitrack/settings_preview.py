"""
Settings de préversion locale : SQLite fichier, pour lancer l'appli sans
PostgreSQL (audit UI/UX, démos). Base jetable dans le dossier du projet.
"""

import os

from .settings import *  # noqa: F401,F403
from .settings import BASE_DIR

DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'preview_db.sqlite3'),
    }
}
