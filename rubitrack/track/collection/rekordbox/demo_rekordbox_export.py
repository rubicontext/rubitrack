#!/usr/bin/env python3
"""
Script de démonstration du service d'export de cue points vers Rekordbox
"""

import os
import sys
import tempfile

# Configuration Django
sys.path.append('/mnt/c/Users/antoine.carnet/work/perso/rubitrack/rubitrack')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rubitrack.settings')

import django
django.setup()

from track.collection.rekordbox.collection_export_service import add_cue_points_to_rekordbox_collection
from track.models import Track


def demo_rekordbox_export():
    """
    Démonstration du service d'export vers Rekordbox
    """
    print("🎧 === DÉMONSTRATION EXPORT RUBITRACK → REKORDBOX === 🎧\n")
    
    # 1. Statistiques des cue points dans Rubitrack
    print("📊 Analyse de la base Rubitrack:")
    total_tracks = Track.objects.count()
    tracks_with_cues = Track.objects.filter(cue_points__isnull=False).count()
    
    print(f"   Total tracks: {total_tracks}")
    print(f"   Tracks avec cue points: {tracks_with_cues}")
    print(f"   Pourcentage: {(tracks_with_cues/total_tracks*100):.1f}%" if total_tracks > 0 else "   Pourcentage: 0%")
    
    # 2. Exemples de tracks avec cue points
    print(f"\n🎵 Exemples de tracks avec cue points:")
    example_tracks = Track.objects.filter(cue_points__isnull=False).select_related('artist')[:5]
    
    for i, track in enumerate(example_tracks, 1):
        cue_points = track.cue_points.get_cue_points_for_export()
        print(f"   {i}. {track.artist.name if track.artist else 'Unknown'} - {track.title}")
        print(f"      → {len(cue_points)} cue points")
        
        # Afficher les 3 premiers cue points
        for cue_num, time_sec in cue_points[:3]:
            minutes = int(time_sec // 60)
            seconds = time_sec % 60
            print(f"        Cue {cue_num}: {minutes}:{seconds:05.2f}")
    
    # 3. Création d'un exemple de collection Rekordbox
    print(f"\n🔧 Création d'une collection Rekordbox de test...")
    
    # Utiliser une vraie track de la base pour la démo
    if example_tracks:
        demo_track = example_tracks[0]
        collection_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<DJ_PLAYLISTS Version="1.0.0">
  <PRODUCT Name="rekordbox" Version="6.0.0" Company="Pioneer DJ"/>
  <COLLECTION Entries="1">
    <TRACK TrackID="1" Name="{demo_track.title}" Artist="{demo_track.artist.name if demo_track.artist else 'Unknown'}" 
           Composer="" Album="" Grouping="" Genre="Electronic" Kind="MP3 File" 
           Size="5000000" TotalTime="180" DiscNumber="0" TrackNumber="0" Year="2023" 
           AverageBpm="128.00" DateAdded="2023-01-01" BitRate="320" SampleRate="44100" 
           Comments="" PlayCount="0" Rating="0" Location="file://localhost/demo.mp3" 
           Remixer="" Tonality="" Label="" Mix=""/>
  </COLLECTION>
  <PLAYLISTS>
  </PLAYLISTS>
</DJ_PLAYLISTS>"""
        
        # Créer un fichier temporaire
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as temp_file:
            temp_file.write(collection_xml)
            temp_collection_path = temp_file.name
        
        print(f"   ✅ Collection de test créée: {os.path.basename(temp_collection_path)}")
        print(f"   📝 Contient: {demo_track.artist.name if demo_track.artist else 'Unknown'} - {demo_track.title}")
        
        # 4. Lancer l'export
        print(f"\n🚀 Lancement de l'export...")
        
        output_path = temp_collection_path.replace('.xml', '_with_cues.xml')
        
        try:
            stats = add_cue_points_to_rekordbox_collection(
                collection_file_path=temp_collection_path,
                output_file_path=output_path
            )
            
            print(f"\n📈 Résultats de l'export:")
            print(f"   Succès: {'✅' if stats['success'] else '❌'}")
            print(f"   Tracks traitées: {stats['tracks_processed']}")
            print(f"   Tracks trouvées: {stats['tracks_matched']}")
            print(f"   Cue points ajoutés: {stats['cue_points_added']}")
            
            # 5. Vérifier le résultat
            if stats['success'] and os.path.exists(output_path):
                print(f"\n🔍 Vérification du fichier généré:")
                
                with open(output_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    position_marks = content.count('<POSITION_MARK')
                    print(f"   Balises POSITION_MARK trouvées: {position_marks}")
                    
                    if position_marks > 0:
                        print(f"   ✅ Cue points ajoutés avec succès!")
                        
                        # Afficher un extrait du XML généré
                        import xml.etree.ElementTree as ET
                        tree = ET.parse(output_path)
                        root = tree.getroot()
                        
                        track = root.find('.//TRACK')
                        if track is not None:
                            print(f"\n📋 Extrait du XML généré:")
                            for position_mark in track.findall('POSITION_MARK'):
                                name = position_mark.get('Name')
                                start = position_mark.get('Start')
                                seconds = float(start) / 44100 if start else 0
                                print(f"      {name}: {seconds:.2f}s (Sample: {start})")
                    else:
                        print(f"   ⚠️  Aucun cue point trouvé dans le fichier")
            
            # Nettoyage
            try:
                os.unlink(temp_collection_path)
                os.unlink(output_path)
                print(f"\n🧹 Fichiers temporaires supprimés")
            except OSError:
                print(f"\n⚠️  Fichiers temporaires non supprimés")
            
        except Exception as e:
            print(f"\n❌ Erreur lors de l'export: {e}")
            import traceback
            traceback.print_exc()
    
    else:
        print("   ❌ Aucune track avec cue points trouvée pour la démonstration")
    
    # 6. Instructions pour l'utilisation réelle
    print(f"\n📚 Pour utiliser ce service avec votre collection Rekordbox:")
    print(f"   1. Localisez votre fichier collection.xml Rekordbox")
    print(f"   2. Créez une sauvegarde: cp collection.xml collection.xml.backup")
    print(f"   3. Utilisez le script: python export_to_rekordbox.py")
    print(f"   4. Ou utilisez directement le service:")
    print(f"      ```python")
    print(f"      from track.collection_export_service import add_cue_points_to_rekordbox_collection")
    print(f"      stats = add_cue_points_to_rekordbox_collection('/path/to/collection.xml')")
    print(f"      ```")
    print(f"   5. Redémarrez Rekordbox pour voir les nouveaux cue points")
    
    print(f"\n✨ Démonstration terminée!")


if __name__ == "__main__":
    try:
        demo_rekordbox_export()
    except Exception as e:
        print(f"❌ Erreur lors de la démonstration: {e}")
        import traceback
        traceback.print_exc()
