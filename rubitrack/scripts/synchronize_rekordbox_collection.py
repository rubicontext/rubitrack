#!/usr/bin/env python
"""
Script pour synchroniser les cue points de Rubitrack vers une collection Rekordbox
"""

import os
import sys

# Ajouter le répertoire parent au path Python
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django

# Configuration de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rubitrack.settings')
django.setup()

from track.collection.rekordbox.synchronize_rekordbox_collection import synchronize_rekordbox_collection


def main():
    """
    Script principal pour synchroniser les cue points
    """
    if len(sys.argv) < 2:
        print("Usage: python synchronize_rekordbox_collection.py <fichier_collection.xml> [fichier_sortie.xml] [mode]")
        print("Modes: overwrite (défaut) ou add_only")
        print("Exemples:")
        print("  python synchronize_rekordbox_collection.py /path/to/collection.xml")
        print("  python synchronize_rekordbox_collection.py /path/to/collection.xml /path/to/collection_updated.xml add_only")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    mode = sys.argv[3] if len(sys.argv) > 3 else 'overwrite'

    if not os.path.exists(input_file):
        print(f"Erreur: Le fichier {input_file} n'existe pas")
        sys.exit(1)

    print("Synchronisation des cue points...")
    print(f"Fichier d'entrée: {input_file}")
    print(f"Fichier de sortie: {output_file or input_file + ' (remplace l original)'}")
    print(f"Mode: {mode}")
    print()

    # Synchronisation
    stats = synchronize_rekordbox_collection(input_file, output_file, mode=mode)

    # Affichage des résultats
    if stats['success']:
        print("✅ Synchronisation réussie!")
        print(f"   - Tracks Rubitrack avec cue points: {stats['rubitrack_tracks_processed']}")
        print(f"   - Tracks Rekordbox matchées: {stats['tracks_found_and_matched']}")
        print(f"   - Tracks mises à jour: {stats['tracks_updated_with_cue_points']}")
        print(f"   - Cue points ajoutés: {stats['total_cue_points_added']}")
        print(f"   - Tracks Rekordbox non trouvées: {len(stats['unmatched_rekordbox_tracks'])}")
    else:
        print("❌ Erreur lors de la synchronisation:")
        print(f"   {stats.get('error', 'Erreur inconnue')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
