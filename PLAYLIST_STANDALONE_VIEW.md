# Playlist List - Standalone View

## 📋 Aperçu

Page dédiée pour gérer les playlists sans dépendre de l'interface admin Django native.
Cela résout les problèmes de rendu liés au menu admin sur différentes tailles d'écran.

## 🔗 URLs

- **Page standalone** : `http://127.0.0.1:8033/track/playlists/`
- **Toggle favourite API** : `http://127.0.0.1:8033/track/toggle_playlist_favourite/`
- **Playlist Favourite** : `http://127.0.0.1:8033/track/playlist_favourite/`

## ✨ Fonctionnalités

### 1. Liste complète des playlists
- Affichage de toutes les playlists triées par rang
- Recherche en temps réel (avec debounce)
- Design responsive sans menu admin

### 2. Système d'étoiles pour les favoris
- ⭐ Colonne avec étoile cliquable
- ★ (or) = playlist favorite
- ☆ (gris) = playlist non-favorite
- Animation au hover (scale 1.3)
- Toggle AJAX instantané

### 3. Actions disponibles
- **Transitions** : Lien vers la page des transitions de la playlist
- **Edit** : Lien vers l'admin Django (nouvelle fenêtre)
- **View Favourites** : Accès rapide aux playlists favorites

### 4. Recherche
- Recherche par nom de playlist
- Auto-submit après 500ms (debounce)
- Compteur de résultats

## 📁 Fichiers créés/modifiés

### Backend
- `/track/playlist/playlist_list_view.py` - Vue principale
- `/track/playlist/toggle_favourite.py` - API AJAX pour toggle
- `/track/urls.py` - Routes ajoutées

### Frontend
- `/track/templates/track/playlists/playlist_list.html` - Template standalone
- `/templates/admin/track/playlist/change_list.html` - Lien ajouté

## 🎨 Design

### Palette de couleurs
- **Background** : #f5f7fa (gris clair)
- **Header** : Gradient #283C4F → #1a2937 (bleu foncé)
- **Accent** : #52d3aa (vert-bleu)
- **Étoile remplie** : #FFD700 (or)
- **Étoile vide** : #ccc (gris)

### Layout
```
┌─────────────────────────────────────────┐
│ Page Header (gradient bleu)            │
│  Playlists                              │
│  Manage your playlists and mark...     │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Action Bar                              │
│  [Search box]      [View Favourites]   │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ ⭐ │ Name         │ ID  │ Actions       │
├────┼──────────────┼─────┼───────────────┤
│ ★  │ Playlist 1   │ #12 │ [Trans][Edit] │
│ ☆  │ Playlist 2   │ #45 │ [Trans][Edit] │
└─────────────────────────────────────────┘
```

## 🔧 Utilisation

### Pour l'utilisateur
1. Accédez à `http://127.0.0.1:8033/track/playlists/`
2. Cliquez sur ☆ pour ajouter aux favoris → devient ★
3. Cliquez sur ★ pour retirer des favoris → devient ☆
4. Utilisez la barre de recherche pour filtrer
5. Cliquez sur "Transitions" pour voir les transitions
6. Cliquez sur "Edit" pour modifier dans l'admin

### Pour le développeur

**Vue principale** :
```python
from .playlist.playlist_list_view import playlist_list_view

# URL : /track/playlists/
# Template : track/playlists/playlist_list.html
# Context : playlists, search_query, total_count, favourite_ids
```

**API Toggle** :
```python
from .playlist.toggle_favourite import toggle_playlist_favourite

# URL : /track/toggle_playlist_favourite/
# Method : POST
# Data : playlist_id
# Response : {success, is_favourite, favourites}
```

## 📱 Responsive

- **Desktop** : Tableau complet avec toutes les colonnes
- **Tablet/Mobile** : Action bar en colonne, tableau scrollable

## 🔄 Synchronisation

Les favoris sont stockés dans `Config.default_playlist_favourites` :
- Format : `"634;611;621;616;630"` (IDs séparés par `;`)
- Modifiable via :
  - Page standalone (étoile cliquable)
  - Admin Django (étoile cliquable)
  - Page de configuration
  - API toggle_playlist_favourite

## ⚡ Performance

- Select_related sur `collection` pour réduire les requêtes
- Tri en Python pour utiliser `get_order_rank()` existant
- AJAX pour toggle instantané sans rechargement
- Debounce sur la recherche (500ms)

## 🐛 Avantages vs Admin Django

✅ **Pas de menu admin** → pas de conflits de layout  
✅ **Contrôle total du CSS** → design personnalisé  
✅ **Responsive natif** → fonctionne sur mobile  
✅ **Recherche optimisée** → auto-submit avec debounce  
✅ **Actions claires** → boutons visibles et accessibles  

## 🚀 Améliorations futures possibles

- [ ] Pagination si >100 playlists
- [ ] Filtrage par année (2025, 2024, etc.)
- [ ] Tri par colonne (nom, ID, favoris)
- [ ] Export CSV des playlists
- [ ] Bulk actions (multi-select)
- [ ] Statistiques par playlist (nb tracks, durée)
