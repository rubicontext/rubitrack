"""
Service pour l'export et la manipulation des collections Rekordbox
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
from .models import Track, TrackCuePoints
import os
import logging

logger = logging.getLogger(__name__)


class RekordboxCollectionExportService:
    """
    Service pour exporter et manipuler les collections Rekordbox
    """
    
    def __init__(self):
        self.collection_tree = None
        self.collection_root = None
    
    def load_rekordbox_collection(self, file_path):
        """
        Charge un fichier collection Rekordbox XML
        
        Args:
            file_path (str): Chemin vers le fichier collection.xml Rekordbox
            
        Returns:
            bool: True si le chargement a réussi, False sinon
        """
        try:
            self.collection_tree = ET.parse(file_path)
            self.collection_root = self.collection_tree.getroot()
            logger.info(f"Collection Rekordbox chargée depuis {file_path}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la collection Rekordbox: {e}")
            return False
    
    def save_rekordbox_collection(self, output_path):
        """
        Sauvegarde la collection Rekordbox modifiée
        
        Args:
            output_path (str): Chemin de sortie pour le fichier collection.xml
            
        Returns:
            bool: True si la sauvegarde a réussi, False sinon
        """
        try:
            # Formatage XML avec indentation
            rough_string = ET.tostring(self.collection_root, 'utf-8')
            reparsed = minidom.parseString(rough_string)
            pretty_xml = reparsed.toprettyxml(indent="  ")
            
            # Suppression de la première ligne générée par minidom
            pretty_xml = '\n'.join(pretty_xml.split('\n')[1:])
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(pretty_xml)
            
            logger.info(f"Collection Rekordbox sauvegardée vers {output_path}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de la collection Rekordbox: {e}")
            return False
    
    def find_track_in_collection(self, artist_name, track_title):
        """
        Trouve une track dans la collection Rekordbox par artiste et titre
        
        Args:
            artist_name (str): Nom de l'artiste
            track_title (str): Titre de la track
            
        Returns:
            ET.Element: L'élément XML de la track trouvée, None sinon
        """
        if not self.collection_root:
            return None
        
        # Recherche dans la collection
        collection = self.collection_root.find('.//COLLECTION')
        if collection is None:
            return None
        
        for track_element in collection.findall('TRACK'):
            track_artist = track_element.get('Artist', '').strip()
            track_name = track_element.get('Name', '').strip()
            
            # Comparaison exacte (insensible à la casse)
            if (track_artist.lower() == artist_name.lower() and 
                track_name.lower() == track_title.lower()):
                return track_element
        
        return None
    
    def seconds_to_position_mark(self, seconds):
        """
        Convertit un temps en secondes en format position mark Rekordbox
        
        Args:
            seconds (float): Temps en secondes
            
        Returns:
            str: Position mark au format Rekordbox (sample position)
        """
        # Rekordbox utilise généralement des samples à 44100 Hz
        # Position = secondes * sample_rate
        sample_rate = 44100
        position = int(seconds * sample_rate)
        return str(position)
    
    def add_cue_points_to_track_element(self, track_element, cue_points):
        """
        Ajoute les cue points à un élément track XML Rekordbox
        
        Args:
            track_element (ET.Element): L'élément XML de la track
            cue_points (list): Liste des cue points [(num, time_seconds), ...]
        """
        # Supprimer les cue points existants
        for cue in track_element.findall('POSITION_MARK'):
            track_element.remove(cue)
        
        # Ajouter les nouveaux cue points
        for cue_num, time_seconds in cue_points:
            if time_seconds is not None and time_seconds > 0:
                position_mark = ET.SubElement(track_element, 'POSITION_MARK')
                position_mark.set('Name', f'Cue {cue_num}')
                position_mark.set('Type', '0')  # Type 0 = Cue point
                position_mark.set('Start', self.seconds_to_position_mark(time_seconds))
                position_mark.set('Num', str(cue_num - 1))  # Rekordbox commence à 0
    
    def add_cue_points_to_rekordbox_collection(self, collection_file_path, output_file_path=None):
        """
        Ajoute les cue points de Rubitrack à une collection Rekordbox
        
        Args:
            collection_file_path (str): Chemin vers le fichier collection.xml Rekordbox
            output_file_path (str, optional): Chemin de sortie. Si None, remplace le fichier original
            
        Returns:
            dict: Statistiques de l'opération
        """
        if output_file_path is None:
            output_file_path = collection_file_path
        
        # Chargement de la collection Rekordbox
        if not self.load_rekordbox_collection(collection_file_path):
            return {
                'success': False,
                'error': 'Impossible de charger la collection Rekordbox'
            }
        
        # Statistiques
        stats = {
            'success': True,
            'tracks_processed': 0,
            'tracks_matched': 0,
            'cue_points_added': 0,
            'tracks_with_cue_points': 0
        }
        
        # Récupération de toutes les tracks Rubitrack avec des cue points
        rubitrack_tracks = Track.objects.filter(
            cue_points__isnull=False  # Utilise le related_name 'cue_points'
        ).select_related('artist', 'cue_points')
        
        logger.info(f"Traitement de {rubitrack_tracks.count()} tracks avec cue points")
        
        for rubitrack_track in rubitrack_tracks:
            stats['tracks_processed'] += 1
            
            # Recherche de la track correspondante dans Rekordbox
            rekordbox_track = self.find_track_in_collection(
                rubitrack_track.artist.name if rubitrack_track.artist else '',
                rubitrack_track.title
            )
            
            if rekordbox_track is not None:
                stats['tracks_matched'] += 1
                
                # Récupération des cue points depuis Rubitrack
                try:
                    track_cue_points = rubitrack_track.cue_points  # Utilise le related_name
                    cue_points_data = track_cue_points.get_cue_points_for_export()
                    
                    if cue_points_data:
                        # Ajout des cue points à la track Rekordbox
                        self.add_cue_points_to_track_element(rekordbox_track, cue_points_data)
                        stats['tracks_with_cue_points'] += 1
                        stats['cue_points_added'] += len(cue_points_data)
                        
                        logger.debug(f"Cue points ajoutés pour: {rubitrack_track.artist.name} - {rubitrack_track.title}")
                
                except Exception as e:
                    logger.error(f"Erreur lors de l'ajout des cue points pour {rubitrack_track.title}: {e}")
        
        # Sauvegarde de la collection modifiée
        if self.save_rekordbox_collection(output_file_path):
            logger.info(f"Export terminé - {stats['tracks_matched']} tracks trouvées, "
                       f"{stats['tracks_with_cue_points']} tracks avec cue points, "
                       f"{stats['cue_points_added']} cue points ajoutés")
        else:
            stats['success'] = False
            stats['error'] = 'Erreur lors de la sauvegarde'
        
        return stats


def add_cue_points_to_rekordbox_collection(collection_file_path, output_file_path=None):
    """
    Fonction utilitaire pour ajouter les cue points à une collection Rekordbox
    
    Args:
        collection_file_path (str): Chemin vers le fichier collection.xml Rekordbox
        output_file_path (str, optional): Chemin de sortie. Si None, remplace le fichier original
        
    Returns:
        dict: Statistiques de l'opération
    """
    service = RekordboxCollectionExportService()
    return service.add_cue_points_to_rekordbox_collection(collection_file_path, output_file_path)


# Fonction pour usage en ligne de commande ou script
def export_cue_points_to_rekordbox(collection_path, output_path=None):
    """
    Export les cue points de Rubitrack vers une collection Rekordbox
    
    Usage:
        from track.collection_export_service import export_cue_points_to_rekordbox
        
        stats = export_cue_points_to_rekordbox(
            '/path/to/rekordbox/collection.xml',
            '/path/to/output/collection_with_cues.xml'
        )
        print(f"Export terminé: {stats}")
    """
    return add_cue_points_to_rekordbox_collection(collection_path, output_path)
