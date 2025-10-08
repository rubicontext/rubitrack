#!/usr/bin/env python3
"""
Script pour créer des cue points de test et vérifier l'affichage
"""

import os
import sys
import django

# Configuration Django
sys.path.append('/mnt/c/Users/antoine.carnet/work/perso/rubitrack/rubitrack')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rubitrack.settings')
django.setup()

from track.models import Track, TrackCuePoints, CuePoint

def create_test_cue_points():
    print("=== Création de cue points de test ===")
    
    # Prenons la première track
    track = Track.objects.first()
    if not track:
        print("Aucune track trouvée")
        return
    
    print(f"Track sélectionnée: {track.title}")
    
    # Créons ou récupérons l'objet TrackCuePoints
    track_cue_points, created = TrackCuePoints.objects.get_or_create(track=track)
    
    if created:
        print("Nouvel objet TrackCuePoints créé")
    else:
        print("Objet TrackCuePoints existant trouvé")
    
    # Créons des cue points de test
    cue_points_data = [
        (1, "0:15", "cue_in", "Intro"),
        (2, "0:45", "beat", "First Drop"),
        (3, "1:30", "beat", "Break"),
        (4, "2:15", "beat", "Second Drop"),
        (5, "3:00", "cue_out", "Outro Start"),
        (6, "3:30", "cue_out", "End")
    ]
    
    for position, time, cue_type, comment in cue_points_data:
        # Créons le cue point
        cue_point, created = CuePoint.objects.get_or_create(
            time=time,
            defaults={
                'type': cue_type,  # Correction: 'type' au lieu de 'cue_type'
                'comment': comment
            }
        )
        
        # Assignons le cue point à la position appropriée
        setattr(track_cue_points, f'cue_point_{position}', cue_point)
        if created:
            print(f"Cue point {position} créé: {time}")
        else:
            print(f"Cue point {position} assigné: {time}")
    
    track_cue_points.save()
    
    # Test des méthodes
    print(f"\nTest des méthodes:")
    print(f"get_track_cue_points_text(): {track.get_track_cue_points_text()}")
    
    cue_points = track_cue_points.get_cue_points()
    print(f"get_cue_points() length: {len(cue_points)}")
    
    non_null_cue_points = [cp for cp in cue_points if cp is not None]
    print(f"Cue points non null: {len(non_null_cue_points)}")
    
    for i, cp in enumerate(cue_points):
        if cp:
            print(f"  Cue point {i+1}: {cp.time} - {cp.comment}")
    
    print(f"\nTrack ID pour les tests: {track.id}")
    print(f"URL de test: /track/history_editing/{track.id}/")

if __name__ == "__main__":
    create_test_cue_points()
