#!/usr/bin/env python3
"""
Exemple d'utilisation du service d'export de cue points vers Rekordbox
"""

import os
import sys

# Configuration Django
sys.path.append('/mnt/c/Users/antoine.carnet/work/perso/rubitrack/rubitrack')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rubitrack.settings')

import django
django.setup()

from track.collection.rekordbox.export_service import add_cue_points_to_rekordbox_collection


def export_cue_points_example():
    """
    Exemple d'utilisation pour exporter les cue points vers Rekordbox
    """
    print("=== Export de cue points vers Rekordbox ===\n")
    
    # Chemin vers votre collection Rekordbox
    # Modifiez ce chemin selon votre installation
    rekordbox_collection_path = input("Chemin vers votre collection.xml Rekordbox: ").strip()
    
    if not rekordbox_collection_path:
        print("Exemple avec un chemin par défaut...")
        rekordbox_collection_path = "/path/to/rekordbox/collection.xml"
    
    # Vérifier que le fichier existe
    if not os.path.exists(rekordbox_collection_path):
        print(f"❌ Fichier non trouvé: {rekordbox_collection_path}")
        print("\nVeuillez fournir le chemin correct vers votre fichier collection.xml de Rekordbox")
        return
    
    # Créer un fichier de sauvegarde
    backup_path = rekordbox_collection_path + ".backup"
    output_path = rekordbox_collection_path.replace('.xml', '_with_rubitrack_cues.xml')
    
    print(f"Collection source: {rekordbox_collection_path}")
    print(f"Sauvegarde: {backup_path}")  
    print(f"Sortie avec cue points: {output_path}")
    
    # Créer une sauvegarde
    try:
        import shutil
        shutil.copy2(rekordbox_collection_path, backup_path)
        print("✅ Sauvegarde créée")
    except Exception as e:
        print(f"❌ Erreur lors de la création de la sauvegarde: {e}")
        return
    
    # Lancer l'export
    print("\n🚀 Lancement de l'export...")
    
    try:
        stats = add_cue_points_to_rekordbox_collection(
            collection_file_path=rekordbox_collection_path,
            output_file_path=output_path
        )
        
        print("\n📊 Résultats de l'export:")
        print(f"   Succès: {'✅' if stats['success'] else '❌'}")
        
        if stats['success']:
            print(f"   Tracks traitées: {stats['tracks_processed']}")
            print(f"   Tracks trouvées dans Rekordbox: {stats['tracks_matched']}")
            print(f"   Tracks avec cue points ajoutés: {stats['tracks_with_cue_points']}")
            print(f"   Nombre total de cue points ajoutés: {stats['cue_points_added']}")
            
            if stats['tracks_matched'] > 0:
                match_percentage = (stats['tracks_matched'] / stats['tracks_processed']) * 100
                print(f"   Taux de correspondance: {match_percentage:.1f}%")
        else:
            print(f"   Erreur: {stats.get('error', 'Erreur inconnue')}")
    
    except Exception as e:
        print(f"❌ Erreur lors de l'export: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n📋 Instructions post-export:")
    print("1. Vérifiez le fichier de sortie avant de remplacer votre collection originale")
    print("2. Fermez Rekordbox avant de remplacer le fichier collection.xml")
    print("3. Remplacez votre collection.xml par le fichier généré")
    print("4. Redémarrez Rekordbox pour voir les nouveaux cue points")


if __name__ == "__main__":
    export_cue_points_example()
