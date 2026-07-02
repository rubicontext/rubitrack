# rubitrack

Application web Django de gestion de collection DJ : import de collections
Traktor (NML), gestion des tracks/cue points/playlists/transitions, suggestions
de mix, et export des cue points vers Rekordbox.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements-dev.txt
```

## Configuration

Les valeurs sensibles (SECRET_KEY, base de données) se configurent par
variables d'environnement — voir [.env.example](.env.example). Les valeurs par
défaut de `settings.py` permettent de démarrer en dev local sans configuration
(PostgreSQL `rubitrack_dev` sur localhost).

```bash
cd rubitrack
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Tests

La suite tourne sur SQLite en mémoire (pas besoin de PostgreSQL) :

```bash
cd rubitrack
pytest
```

La CI GitHub Actions ([.github/workflows/tests.yml](.github/workflows/tests.yml))
lance ruff + pytest sur chaque push et pull request.

## Fonctionnalités principales

- **Import Traktor** : upload du `collection.nml` (tracks, cue points, playlists)
- **Export Rekordbox** : injection des cue points dans un `rekordbox.xml`
  (`/track/rekordbox/`), modes écrasement ou ajout seul
- **Currently playing** : suivi du morceau en cours (log Icecast), suggestions
  par BPM/clé musicale/ranking, historique des transitions
- **Doublons** : détection et fusion manuelle de tracks/artistes en double
  (y compris équivalences enharmoniques Bbm ↔ A#m)
