# Changements - Page Playlist Favourite

## Date: 2 février 2026

### Modifications effectuées

#### 1. Amélioration visuelle des noms de playlists
- **Fichier modifié**: `track/templates/track/playlists/playlist_favourite.html`
- **Changement**: Augmentation de la taille de police des noms de playlists de 14px à 22px
- **Impact**: Les noms de playlists sont maintenant beaucoup plus visibles et lisibles
- **Style appliqué**: 
  - Taille de police: 22px
  - Font-weight: bold
  - Couleur: #283C4F (bleu foncé)
  - Marges: 20px en haut, 8px en bas pour une meilleure séparation

#### 2. Migration du paramètre de playlists favorites vers la base de données
- **Fichiers modifiés**:
  - `track/models.py` - Ajout du champ `default_playlist_favourites` au modèle Config
  - `track/playlist/playlist_favourite.py` - Utilisation du paramètre depuis Config au lieu de la constante
  - `track/config/config_views.py` - Ajout du champ dans la fonction de reset
  - `track/templates/track/config/config_form.html` - Ajout du champ dans le formulaire

- **Nouveau champ dans Config**:
  ```python
  default_playlist_favourites = models.CharField(
      max_length=500,
      default="634;611;621;616;630",
      help_text="Default favourite playlist IDs (semicolon-separated)"
  )
  ```

- **Migration créée**: `0023_add_default_playlist_favourites.py`

#### 3. Configuration dynamique
- **Avant**: La liste des playlists favorites était définie en dur dans une constante `DEFAULT_PLAYLIST_FAVOURITES`
- **Après**: La liste est stockée dans la base de données et peut être modifiée via l'interface web
- **Page de configuration**: Tools > Config (déjà existante)
- **Nouvelle section**: "Paramètres des playlists" avec le champ "Playlists favorites par défaut"

### Comment utiliser

1. **Modifier les playlists favorites par défaut**:
   - Aller sur la page Tools > Config
   - Chercher la section "Paramètres des playlists"
   - Modifier le champ "Playlists favorites par défaut"
   - Format: IDs séparés par des points-virgules (ex: "634;611;621;616;630")
   - Cliquer sur "Sauvegarder la configuration"

2. **Visualiser les playlists favorites**:
   - Aller sur la page Playlist Favourite
   - Les playlists définies par défaut seront affichées automatiquement
   - Les noms des playlists sont maintenant affichés en grand et en gras

### Migration de base de données

Pour appliquer les changements en base de données:
```bash
cd rubitrack
python3 manage.py migrate track
```

Cette commande appliquera la migration `0023_add_default_playlist_favourites` qui ajoute le nouveau champ à la table Config.

### Notes techniques

- Le champ accepte jusqu'à 500 caractères (suffisant pour ~50 IDs de playlists)
- La valeur par défaut reste "634;611;621;616;630" pour assurer la compatibilité
- Le formulaire de configuration affiche automatiquement tous les champs du modèle Config
- La fonction de reset de configuration inclut maintenant la valeur par défaut des playlists favorites
