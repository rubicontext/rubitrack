#!/usr/bin/env python3
"""
Script pour ajouter des données de test comment, ranking et playcount
"""

import os
import sys
import django
import random

# Configuration Django
sys.path.append('/mnt/c/Users/antoine.carnet/work/perso/rubitrack/rubitrack')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rubitrack.settings')
django.setup()

from track.models import Track

def add_test_data():
    print("=== Ajout de données de test ===")
    
    tracks = Track.objects.all()[:20]  # Prenons les 20 premières tracks
    
    comments_test = [
        "Excellent morceau pour les fins de soirée",
        "Track énergique parfaite pour les warm-up",
        "Mélodie accrocheuse et drops puissants",
        "Version remix très réussie",
        "Classic intemporel du genre",
        "Production impeccable et mastering parfait",
        "Track underground très recherchée",
        "Parfait pour les transitions",
        "Hymne de la scène électronique",
        "Découverte récente, très prometteuse"
    ]
    
    for track in tracks:
        # Ajouter un commentaire aléatoire si vide
        if not track.comment:
            track.comment = random.choice(comments_test)
        
        # Ajouter un ranking aléatoire si vide
        if not track.ranking or track.ranking == 0:
            track.ranking = random.randint(1, 5)
        
        # Ajouter un playcount aléatoire si vide
        if not track.playcount or track.playcount == 0:
            track.playcount = random.randint(1, 50)
        
        track.save()
        print(f"Mis à jour: {track.title[:30]}... - Ranking: {track.ranking}, Playcount: {track.playcount}")
    
    print(f"Données de test ajoutées pour {len(tracks)} tracks")

if __name__ == "__main__":
    add_test_data()
