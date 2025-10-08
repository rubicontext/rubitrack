#!/usr/bin/env python3
"""
Script pour déboguer les cue points et ranking
"""

import os
import sys
import django

# Configuration Django
sys.path.append('/mnt/c/Users/antoine.carnet/work/perso/rubitrack/rubitrack')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rubitrack.settings')
django.setup()

from track.models import Track, TrackCuePoints, CuePoint

def debug_cue_points_and_ranking():
    print("=== Debug Cue Points et Ranking ===")
    
    # Vérifier les tracks avec des rankings non nuls
    tracks_with_ranking = Track.objects.filter(ranking__gt=0)
    print(f"Tracks avec ranking > 0: {tracks_with_ranking.count()}")
    
    # Vérifier les tracks avec des cue points
    tracks_with_cuepoints = Track.objects.filter(cue_points__isnull=False)
    print(f"Tracks avec cue points: {tracks_with_cuepoints.count()}")
    
    # Vérifier quelques tracks spécifiques
    tracks = Track.objects.all()[:10]
    
    print("\n--- Détails des 10 premières tracks ---")
    for track in tracks:
        print(f"\nTrack: {track.title[:40]}...")
        print(f"  ID: {track.id}")
        print(f"  Ranking: {track.ranking} (type: {type(track.ranking)})")
        
        # Vérifier les cue points
        try:
            if hasattr(track, 'cue_points') and track.cue_points:
                cue_points_text = track.get_track_cue_points_text()
                print(f"  Cue Points: {cue_points_text}")
                
                # Détails des cue points
                cue_points = track.cue_points.get_cue_points()
                cue_points_count = len([cp for cp in cue_points if cp is not None])
                print(f"  Nombre de cue points: {cue_points_count}")
            else:
                print(f"  Cue Points: Aucun")
        except Exception as e:
            print(f"  Cue Points: Erreur - {e}")
    
    # Test spécifique d'une track avec cue points si elle existe
    if tracks_with_cuepoints.exists():
        test_track = tracks_with_cuepoints.first()
        print(f"\n--- Test spécifique track avec cue points ---")
        print(f"Track: {test_track.title}")
        print(f"ID: {test_track.id}")
        print(f"Relation cue_points existe: {hasattr(test_track, 'cue_points')}")
        
        if hasattr(test_track, 'cue_points'):
            print(f"Cue_points object: {test_track.cue_points}")
            try:
                cue_points = test_track.cue_points.get_cue_points()
                print(f"get_cue_points() result: {cue_points}")
                print(f"get_track_cue_points_text(): {test_track.get_track_cue_points_text()}")
            except Exception as e:
                print(f"Erreur lors de l'accès aux cue points: {e}")

def fix_rankings():
    """
    Corrige les rankings NULL en les mettant à 0
    """
    print("\n=== Correction des rankings NULL ===")
    tracks_with_null_ranking = Track.objects.filter(ranking__isnull=True)
    count = tracks_with_null_ranking.count()
    
    if count > 0:
        print(f"Trouvé {count} tracks avec ranking NULL")
        tracks_with_null_ranking.update(ranking=0)
        print(f"Mis à jour {count} tracks avec ranking=0")
    else:
        print("Aucune track avec ranking NULL trouvée")

if __name__ == "__main__":
    debug_cue_points_and_ranking()
    fix_rankings()
