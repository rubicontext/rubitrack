# Module de Synchronisation Rekordbox - Cue Points

Ce module se concentre **uniquement** sur la synchronisation des cue points entre Rubitrack et Rekordbox, sans toucher aux autres données.

## Fichiers créés

### 1. `/track/collection/rekordbox/synchronize_rekordbox_collection.py`
**Module principal** - Service simple et fiable pour synchroniser les cue points :
- Charge un fichier XML Rekordbox
- Trouve les tracks correspondantes (par artiste + titre)
- Supprime les cue points existants
- Ajoute les cue points de Rubitrack
- Sauvegarde le fichier modifié

### 2. `/scripts/synchronize_rekordbox_collection.py`
**Script en ligne de commande** pour utiliser la synchronisation :
```bash
python manage.py runserver  # dans un terminal
# Dans un autre terminal :
cd /mnt/c/Users/antoine.carnet/work/perso/rubitrack/rubitrack
python scripts/synchronize_rekordbox_collection.py /path/to/collection.xml [/path/to/output.xml]
```

### 3. `/track/collection/rekordbox/views.py`
**API Django** pour interface web :
- Upload de fichier XML Rekordbox
- Synchronisation des cue points
- Téléchargement du fichier modifié
- Statistiques des cue points

### 4. `/track/templates/track/rekordbox/sync.html`
**Interface web** avec :
- Statistiques des cue points actuels
- Upload de fichier XML
- Téléchargement automatique du fichier modifié

### 5. **URLs intégrées dans `/track/urls.py`** :
- `/track/rekordbox/` - Interface web
- `/track/rekordbox/api/synchronize/` - API de synchronisation
- `/track/rekordbox/api/stats/` - API des statistiques

## Utilisation

### Via script Python :
```python
from track.collection.rekordbox.synchronize_rekordbox_collection import synchronize_rekordbox_collection

stats = synchronize_rekordbox_collection(
    '/path/to/rekordbox_collection.xml',
    '/path/to/rekordbox_collection_updated.xml'
)
print(f"Résultat: {stats}")
```

### Via ligne de commande :
```bash
python scripts/synchronize_rekordbox_collection.py collection.xml collection_updated.xml
```

### Via interface web :
Accédez à `/track/rekordbox/` dans l'admin Django

## Fonctionnement

1. **Chargement** : Parse le fichier XML Rekordbox
2. **Correspondance** : Trouve les tracks par `Artist` + `Name` (insensible à la casse)
3. **Nettoyage** : Supprime tous les `POSITION_MARK` existants
4. **Ajout** : Ajoute les nouveaux cue points de Rubitrack (format `M:SS` → samples à 44100Hz)
5. **Sauvegarde** : Écrit le fichier XML modifié

## Format des cue points Rekordbox

```xml
<POSITION_MARK Name="Cue 1" Type="0" Start="132300" Num="0"/>
<POSITION_MARK Name="Cue 2" Type="0" Start="264600" Num="1"/>
```

- `Name` : "Cue 1", "Cue 2", etc.
- `Type` : "0" pour cue point
- `Start` : Position en samples (secondes × 44100)
- `Num` : Index commençant à 0

## Sécurité

- **Aucune modification** des autres données du fichier XML
- **Sauvegarde** possible vers un nouveau fichier
- **Validation** du format de fichier
- **Gestion d'erreurs** complète

Le module est conçu pour être **simple, fiable et sûr**.
