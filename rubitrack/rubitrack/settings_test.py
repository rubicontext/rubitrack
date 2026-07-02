"""
Settings de test : identiques aux settings de dev mais avec une base SQLite
en mémoire pour que la suite pytest tourne sans PostgreSQL.
"""

from .settings import *  # noqa: F401,F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}
