-- =============================================================================
-- Script de suppression des tracks contenant "back to black" dans le titre
-- Prend en compte toutes les dépendances
-- =============================================================================
-- ⚠️  TOUJOURS faire un backup avant d'exécuter ce script !
-- sqlite3 db.sqlite3 ".backup backup_before_delete.sqlite3"
-- =============================================================================

-- Afficher les tracks qui vont être supprimées (vérification avant suppression)
SELECT id, title FROM track_track WHERE LOWER(title) LIKE '%back to black%';

-- =============================================================================
-- ETAPE 1 : Retirer les tracks des playlists ManyToMany (track_playlist_tracks)
-- =============================================================================
DELETE FROM track_playlist_tracks
WHERE track_id IN (
    SELECT id FROM track_track WHERE LOWER(title) LIKE '%back to black%'
);

-- =============================================================================
-- ETAPE 2 : Retirer les tracks de la collection ManyToMany (track_collection_tracks)
-- =============================================================================
DELETE FROM track_collection_tracks
WHERE track_id IN (
    SELECT id FROM track_track WHERE LOWER(title) LIKE '%back to black%'
);

-- =============================================================================
-- ETAPE 3 : Supprimer les entrées CurrentlyPlaying liées
-- =============================================================================
DELETE FROM track_currentlyplaying
WHERE track_id IN (
    SELECT id FROM track_track WHERE LOWER(title) LIKE '%back to black%'
);

-- =============================================================================
-- ETAPE 4 : Supprimer les transitions où ces tracks sont source ou destination
-- =============================================================================
DELETE FROM track_transition
WHERE track_source_id IN (
    SELECT id FROM track_track WHERE LOWER(title) LIKE '%back to black%'
)
OR track_destination_id IN (
    SELECT id FROM track_track WHERE LOWER(title) LIKE '%back to black%'
);

-- =============================================================================
-- ETAPE 5 : Supprimer les CuePoints liés via TrackCuePoints
-- D'abord récupérer les IDs des CuePoints référencés, puis les nullifier,
-- puis supprimer le TrackCuePoints, puis supprimer les CuePoints orphelins
-- =============================================================================

-- 5a : Supprimer les TrackCuePoints (les FK vers CuePoint passent à NULL grâce à SET_NULL)
DELETE FROM track_trackcuepoints
WHERE track_id IN (
    SELECT id FROM track_track WHERE LOWER(title) LIKE '%back to black%'
);

-- 5b : Supprimer les CuePoints orphelins (non référencés par aucun TrackCuePoints)
DELETE FROM track_cuepoint
WHERE id NOT IN (
    SELECT cue_point_1_id FROM track_trackcuepoints WHERE cue_point_1_id IS NOT NULL
    UNION SELECT cue_point_2_id FROM track_trackcuepoints WHERE cue_point_2_id IS NOT NULL
    UNION SELECT cue_point_3_id FROM track_trackcuepoints WHERE cue_point_3_id IS NOT NULL
    UNION SELECT cue_point_4_id FROM track_trackcuepoints WHERE cue_point_4_id IS NOT NULL
    UNION SELECT cue_point_5_id FROM track_trackcuepoints WHERE cue_point_5_id IS NOT NULL
    UNION SELECT cue_point_6_id FROM track_trackcuepoints WHERE cue_point_6_id IS NOT NULL
    UNION SELECT cue_point_7_id FROM track_trackcuepoints WHERE cue_point_7_id IS NOT NULL
    UNION SELECT cue_point_8_id FROM track_trackcuepoints WHERE cue_point_8_id IS NOT NULL
);

-- =============================================================================
-- ETAPE 6 : Supprimer les tracks elles-mêmes
-- =============================================================================
DELETE FROM track_track
WHERE LOWER(title) LIKE '%back to black%';

-- =============================================================================
-- Vérification finale : s'assurer que les tracks sont bien supprimées
-- =============================================================================
SELECT COUNT(*) AS remaining FROM track_track WHERE LOWER(title) LIKE '%back to black%';
