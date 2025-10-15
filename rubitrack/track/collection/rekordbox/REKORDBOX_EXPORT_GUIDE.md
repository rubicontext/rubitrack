# Service d'Export de Cue Points vers Rekordbox

## Vue d'ensemble

Le service `export_service.py` (anciennement `collection_export_service.py`) permet d'exporter les cue points stockés dans Rubitrack vers une collection Rekordbox XML. Il recherche les tracks ayant exactement le même nom d'artiste et titre, puis ajoute les cue points correspondants.

## Architecture

### Classes principales

#### `RekordboxCollectionExportService`
Service principal pour manipuler les collections Rekordbox.

**Méthodes principales:**
- `load_rekordbox_collection(file_path)` : Charge un fichier collection.xml
- `find_track_in_collection(artist_name, track_title)` : Trouve une track par artiste/titre
- `add_cue_points_to_rekordbox_collection(collection_file_path, output_file_path)` : Fonction principale d'export

### Modèles Django

#### `TrackCuePoints`
- `get_cue_points_for_export()` : Retourne les cue points au format (numéro, temps_en_secondes)

## Utilisation

### 1. Import du service
```python
from track.collection.rekordbox.export_service import add_cue_points_to_rekordbox_collection
```

### 2. Export basique
```python
stats = add_cue_points_to_rekordbox_collection(
    collection_file_path="/path/to/collection.xml",
    output_file_path="/path/to/collection_with_cues.xml"
)
```

### 3. Export en remplacement
```python
# Remplace le fichier original
stats = add_cue_points_to_rekordbox_collection(
    collection_file_path="/path/to/collection.xml"
)
```

## Format des données

### Cue Points Rubitrack
```python
# Format interne Rubitrack
cue_points = [
    (1, 30.5),   # Cue 1 à 30.5 secondes
    (2, 60.0),   # Cue 2 à 1 minute
    (3, 120.75)  # Cue 3 à 2:00.75
]
```

### Format Rekordbox XML
```xml
<POSITION_MARK Name="Cue 1" Type="0" Start="1345500" Num="0"/>
<POSITION_MARK Name="Cue 2" Type="0" Start="2646000" Num="1"/>
<POSITION_MARK Name="Cue 3" Type="0" Start="5329125" Num="2"/>
```

**Conversion:** `position_samples = secondes * 44100`

## Critères de correspondance

Le service recherche les tracks avec :
- **Artiste identique** (insensible à la casse)
- **Titre identique** (insensible à la casse)

### Exemple de correspondance

**Rubitrack:**
- Artiste: "Nils A"
- Titre: "Trop Tot (Original Mix)"

**Rekordbox:**
```xml
<TRACK Artist="Nils A" Name="Trop Tot (Original Mix)" ...>
```
✅ **Correspondance trouvée**

## Statistiques d'export

La fonction retourne un dictionnaire avec :

```python
{
    'success': True,                    # Succès de l'opération
    'tracks_processed': 150,            # Tracks Rubitrack traitées
    'tracks_matched': 45,               # Tracks trouvées dans Rekordbox
    'tracks_with_cue_points': 42,       # Tracks avec cue points ajoutés
    'cue_points_added': 238,            # Nombre total de cue points
    'error': None                       # Message d'erreur le cas échéant
}
```

## Workflow recommandé

### 1. Préparation
```bash
# Créer une sauvegarde de votre collection Rekordbox
cp collection.xml collection.xml.backup
```

### 2. Export
```python
from track.collection.rekordbox.export_service import add_cue_points_to_rekordbox_collection

stats = add_cue_points_to_rekordbox_collection(
    collection_file_path="collection.xml",
    output_file_path="collection_with_cues.xml"
)

print(f"Export terminé: {stats['cue_points_added']} cue points ajoutés")
```

### 3. Vérification
- Ouvrir `collection_with_cues.xml` dans un éditeur XML
- Vérifier la présence des balises `<POSITION_MARK>`
- Comparer avec la sauvegarde

### 4. Déploiement
```bash
# Fermer Rekordbox
# Remplacer le fichier collection
mv collection_with_cues.xml collection.xml
# Redémarrer Rekordbox
```

## Scripts d'assistance

### Test du service
```bash
python test_rekordbox_export.py
```

### Export interactif
```bash
python export_to_rekordbox.py
```

## Gestion des erreurs

### Erreurs courantes

1. **Fichier collection non trouvé**
```python
# Vérifier l'existence du fichier
if not os.path.exists(collection_path):
    print("Fichier collection non trouvé")
```

2. **XML malformé**
```python
# Le service gère automatiquement les erreurs de parsing
stats = add_cue_points_to_rekordbox_collection(collection_path)
if not stats['success']:
    print(f"Erreur: {stats['error']}")
```

3. **Permissions d'écriture**
```python
# Vérifier les permissions avant l'export
try:
    with open(output_path, 'w') as f:
        pass
except PermissionError:
    print("Permissions insuffisantes")
```

## Limitations

1. **Correspondance exacte uniquement**
   - Pas de correspondance approximative
   - Sensible aux différences de casse et espaces

2. **Format Rekordbox XML uniquement**
   - Ne supporte pas les bases de données binaires
   - Compatible Rekordbox 5.x et 6.x

3. **Conversion de temps fixe**
   - Utilise un sample rate de 44.1 kHz par défaut
   - Peut nécessiter des ajustements pour d'autres formats

## Optimisations futures

1. **Correspondance approximative**
   - Recherche par similarité de chaînes
   - Prise en compte des variations de titre

2. **Support multi-format**
   - Import/export vers d'autres logiciels DJ
   - Support des bases de données binaires

3. **Interface graphique**
   - Outil de mapping interactif
   - Prévisualisation des correspondances

## Exemples d'usage avancé

### Export avec filtres
```python
from track.models import Track
from track.collection.rekordbox.export_service import RekordboxCollectionExportService

# Service personnalisé
service = RekordboxCollectionExportService()
service.load_rekordbox_collection("collection.xml")

# Traitement sélectif
tracks_with_high_ranking = Track.objects.filter(
    cue_points__isnull=False,
    ranking__gte=4
)

for track in tracks_with_high_ranking:
    rekordbox_track = service.find_track_in_collection(
        track.artist.name, 
        track.title
    )
    if rekordbox_track:
        cue_points = track.cue_points.get_cue_points_for_export()
        service.add_cue_points_to_track_element(rekordbox_track, cue_points)

service.save_rekordbox_collection("collection_high_ranking.xml")
```

### Rapport détaillé
```python
def detailed_export_report(collection_path):
    stats = add_cue_points_to_rekordbox_collection(collection_path)
    
    print("=== RAPPORT D'EXPORT DÉTAILLÉ ===")
    print(f"Tracks traitées: {stats['tracks_processed']}")
    print(f"Taux de correspondance: {stats['tracks_matched']/stats['tracks_processed']*100:.1f}%")
    print(f"Cue points par track: {stats['cue_points_added']/stats['tracks_with_cue_points']:.1f}")
    
    return stats
```
