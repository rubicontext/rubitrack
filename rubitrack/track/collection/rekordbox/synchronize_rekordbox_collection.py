"""
Module simple pour synchroniser les cue points entre Rubitrack et Rekordbox
Se concentre uniquement sur le remplacement des cue points, sans toucher aux autres données
"""

import logging
import re
import unicodedata
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Dict, Iterable, Optional, Union
from urllib.parse import unquote, urlparse
from xml.dom import minidom

from ...models import Track

logger = logging.getLogger(__name__)

# Ne pas dupliquer un cue si un marqueur existe déjà à une position très proche (en add_only)
CUE_POINT_IDENTICAL_START_TIME_DIFF_MS = 100


class RekordboxCollectionSynchronizer:
    """
    Service simple pour synchroniser uniquement les cue points entre Rubitrack et Rekordbox
    """
    
    def __init__(self) -> None:
        self.tree: Optional[ET.ElementTree] = None
        self.root: Optional[ET.Element] = None
    
    def load_rekordbox_file(self, file_path: str) -> bool:
        """
        Charge le fichier XML Rekordbox
        
        Args:
            file_path (str): Chemin vers le fichier collection.xml
            
        Returns:
            bool: True si succès, False sinon
        """
        try:
            self.tree = ET.parse(file_path)
            self.root = self.tree.getroot()
            logger.info(f"Fichier Rekordbox chargé: {file_path}")
            return True
        except (ET.ParseError, OSError) as e:
            logger.error(f"Erreur chargement fichier: {e}")
            return False
    
    def save_rekordbox_file(self, output_path: str) -> bool:
        """
        Sauvegarde le fichier XML Rekordbox modifié
        
        Args:
            output_path (str): Chemin de sortie
            
        Returns:
            bool: True si succès, False sinon
        """
        try:
            # Conversion en string XML avec formatage
            rough_string = ET.tostring(self.root, encoding='utf-8')
            reparsed = minidom.parseString(rough_string)
            
            # Formatage avec indentation
            pretty_xml = reparsed.toprettyxml(indent="  ", encoding=None)
            
            # Suppression de la ligne XML générée par minidom et nettoyage
            lines = pretty_xml.split('\n')
            # Garder la première ligne <?xml... mais supprimer les lignes vides en trop
            clean_lines = [lines[0]]  # Déclaration XML
            for line in lines[1:]:
                if line.strip():  # Garder seulement les lignes non vides
                    clean_lines.append(line)
            
            pretty_xml = '\n'.join(clean_lines)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(pretty_xml)
            
            logger.info(f"Fichier sauvegardé: {output_path}")
            return True
        except OSError as e:
            logger.error(f"Erreur sauvegarde: {e}")
            return False
    
    def seconds_to_rekordbox_position(self, seconds: Union[float, Decimal]) -> str:
        """Retourne la position Rekordbox en secondes avec 3 décimales (ex: 33.000), arrondie correctement."""
        try:
            d = seconds if isinstance(seconds, Decimal) else Decimal(str(seconds))
            return f"{d.quantize(Decimal('0.000'), rounding=ROUND_HALF_UP)}"
        except (InvalidOperation, ValueError, TypeError):
            return "0.000"
    
    def _normalize_text(self, s: str) -> str:
        """
        Normalize titles/artists to base forms:
        - Strip key/rating suffixes like " - Am - 6" or trailing " - 6"
        - Remove site watermarks and noise tokens (FREE DOWNLOAD, snippet, HD)
        - Remove bracketed/parenthetical content
        - Unicode NFKC and collapse whitespace
        """
        s = (s or '').strip()
        s = unicodedata.normalize('NFKC', s)
        # remove key/rating suffix like ' - Am - 6'
        s = re.sub(r"\s*-\s*[A-G](?:[#♯♭m])?\s*-\s*\d+\s*$", "", s, flags=re.IGNORECASE)
        # remove trailing rating-only like ' - 6'
        s = re.sub(r"\s*-\s*\d+\s*$", "", s)
        # remove common site/watermark tokens and noise words
        s = re.sub(r"\b(my[- ]?free[- ]?mp3s?\.com|myplaylist[- ]?youtubemp3\.com|myfreemp3\.vip|my[- ]?free[- ]?mp3\.net)\b", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\b(snippet|free\s*download|official\s*video|hd)\b", "", s, flags=re.IGNORECASE)
        # remove bracketed/parenthetical noise like (Original Mix), [Snippet], {YouT}
        s = re.sub(r"[\(\[{].*?[\)\]}]", "", s)
        # collapse whitespace
        s = re.sub(r"\s+", " ", s).strip()
        return s

    @staticmethod
    def _normalize_traktor_path(path: str) -> str:
        """Normalise un chemin Traktor ("C:/:Users/:antoine/:Music/:strobe.mp3")
        vers une forme comparable ("c:/users/antoine/music/strobe.mp3")."""
        return (path or '').replace('/:', '/').lower()

    @staticmethod
    def _normalize_rekordbox_location(location: str) -> str:
        """Normalise l'attribut Location d'un TRACK Rekordbox
        ("file://localhost/C:/Program%20Files/x.mp3") vers la même forme
        comparable que _normalize_traktor_path ("c:/program files/x.mp3")."""
        if not location:
            return ''
        if location.startswith('file://'):
            path = unquote(urlparse(location).path)
            # "/C:/Users/..." -> "C:/Users/..."
            if len(path) >= 3 and path[0] == '/' and path[2] == ':':
                path = path[1:]
            return path.lower()
        return unquote(location).lower()

    def remove_existing_cue_points(self, track_element: ET.Element) -> None:
        """
        Supprime tous les cue points existants d'une track

        Args:
            track_element (ET.Element): Élément TRACK
        """
        # Supprimer tous les éléments POSITION_MARK (cue points)
        for position_mark in track_element.findall('POSITION_MARK'):
            track_element.remove(position_mark)
    
    def add_cue_point_to_track(
        self,
        track_element: ET.Element,
        time_seconds: float,
        name: str,
        num_value: int,
        end_seconds: Optional[float] = None,
        force_loop: bool = False,
    ) -> None:
        """
        Ajoute un cue point à une track Rekordbox.
        - Si end_seconds est fourni et > start OU force_loop=True: export en loop (Type 4) avec couleurs orange.
          Si un num_value (0..2) est fourni, on positionne aussi Num pour créer une "loop hot cue" (supporté par Rekordbox).
        - Sinon: export en hot cue (Type 0) avec Num et couleurs vertes.
        """
        position_mark = ET.SubElement(track_element, 'POSITION_MARK')
        position_mark.set('Name', name)
        start_value = self.seconds_to_rekordbox_position(time_seconds)
        position_mark.set('Start', start_value)
        # Créer comme loop si: durée définie OU force_loop=True (traktor_type=4 pour cues 4-8)
        if force_loop or (end_seconds is not None and end_seconds > time_seconds):
            # Loop (Type 4) avec couleur orange
            position_mark.set('Type', '4')
            if end_seconds is not None and end_seconds > time_seconds:
                end_value = self.seconds_to_rekordbox_position(end_seconds)
                position_mark.set('End', end_value)
            # S'il s'agit d'un slot hot (0..2), renseigner Num pour qu'elle apparaisse sur le pad correspondant
            if num_value != -1:
                position_mark.set('Num', str(num_value))
            position_mark.set('Red', '255')
            position_mark.set('Green', '140')
            position_mark.set('Blue', '0')
            logger.debug("Add LOOP POSITION_MARK: start=%s end=%s num=%s force_loop=%s", start_value, (end_value if end_seconds else 'None'), (str(num_value) if num_value != -1 else ''), force_loop)
        else:
            # Hot cue (Type 0) avec Num et couleur verte
            position_mark.set('Type', '0')
            position_mark.set('Num', str(num_value))
            position_mark.set('Red', '60')
            position_mark.set('Green', '235')
            position_mark.set('Blue', '80')
            logger.debug("Add HOT POSITION_MARK: start=%s num=%s", start_value, str(num_value))
    
    def remove_system_generated_cue_points(self, track_element: ET.Element) -> None:
        """
        Supprime uniquement les cue points générés par le système (nommage 'RCueX').
        - Supprime TOUT POSITION_MARK dont le Name commence par 'RCue' (Type 0 ou 4)
        - Préserve tous les autres cue points manuels
        - Nettoie aussi les anciens hot cues nommés 'A','B','C' (legacy) en Type 0
        
        Args:
            track_element (ET.Element): Élément TRACK
        """
        for pm in list(track_element.findall('POSITION_MARK')):
            name = pm.get('Name', '')
            pm_type = pm.get('Type')
            if name.startswith('RCue'):
                track_element.remove(pm)
                logger.debug(f"Supprimé cue point système (RCue*): {name}")
            elif pm_type == '0' and name in {'A', 'B', 'C'}:
                track_element.remove(pm)
                logger.debug(f"Supprimé cue point système legacy: {name}")

    def _hot_cue_exists(self, track_element: ET.Element, num: int) -> bool:
        """
        Vérifie si un slot de hot cue (Type 0 ou Type 4 avec Num) est déjà occupé.
        Prend en compte les boucles (Type 4) auxquelles un Num a été attribué.
        
        Args:
            track_element: Élément TRACK
            num: Numéro du slot (0, 1, 2 pour les hot cues)
            
        Returns:
            bool: True si le slot est occupé, False sinon
        """
        for pm in track_element.findall('POSITION_MARK'):
            t = pm.get('Type')
            if t in ('0', '4') and pm.get('Num') == str(num):
                return True
        return False
    
    def _has_existing_cue_near_start(self, track_element: ET.Element, start_seconds: float, diff_ms: int) -> bool:
        """Retourne True si un POSITION_MARK non-RCue existe à +/- diff_ms autour de start_seconds.
        Les marqueurs nommés 'RCue*' ne bloquent pas l'ajout en add_only.
        """
        try:
            delta = Decimal(str(diff_ms)) / Decimal('1000')
            target = Decimal(str(start_seconds))
        except (InvalidOperation, ValueError):
            return False
        for pm in track_element.findall('POSITION_MARK'):
            # Ignorer nos propres marqueurs RCue
            name_attr = pm.get('Name', '') or ''
            if name_attr.startswith('RCue'):
                continue
            s = pm.get('Start')
            if not s:
                continue
            try:
                s_dec = Decimal(str(s))
            except (InvalidOperation, ValueError):
                continue
            if (target - s_dec).copy_abs() <= delta:
                return True
        return False
    
    def synchronize_rekordbox_collection(
        self,
        input_file: str,
        output_file: Optional[str] = None,
        mode: str = 'overwrite'
    ) -> dict:
        """
        Synchronise les cue points de Rubitrack vers Rekordbox
        Modes:
          overwrite : supprime tous les cue points existants puis ajoute tous les RCue1-8
          add_only  : supprime uniquement les cue points système générés (RCueX), préserve les cue points manuels,
                     puis ajoute conditionnellement les nouveaux (slots libres pour 1-3, positions libres pour 4-8)

        Args:
            input_file (str): Fichier Rekordbox d'entrée
            output_file (str, optional): Fichier de sortie (si None, remplace l'original)
            mode (str, optional): Mode de synchronisation ('overwrite' ou 'add_only')

        Returns:
            dict: Statistiques de l'opération
        """
        if output_file is None:
            output_file = input_file

        # Chargement du fichier Rekordbox
        if not self.load_rekordbox_file(input_file):
            return {
                'success': False,
                'error': 'Impossible de charger le fichier Rekordbox'
            }

        # Validation: un export Rekordbox a pour racine DJ_PLAYLISTS
        if self.root.tag != 'DJ_PLAYLISTS':
            return {
                'success': False,
                'error': f"Fichier XML invalide: racine '{self.root.tag}' au lieu de DJ_PLAYLISTS (pas un export Rekordbox)"
            }

        stats = self._initialize_stats()
        collection = self.root.find('.//COLLECTION')
        if collection is not None:
            stats['total_tracks_in_rekordbox_file'] = len(collection.findall('TRACK'))

        rubitrack_tracks = self._get_rubitrack_tracks()
        stats['rubitrack_tracks_processed'] = rubitrack_tracks.count()
        logger.info(f"Traitement de {stats['rubitrack_tracks_processed']} tracks Rubitrack avec cue points")

        rubitrack_lookup = self._build_rubitrack_lookup(rubitrack_tracks)
        self._process_tracks(rubitrack_tracks, collection, stats, mode, rubitrack_lookup)

        if self.save_rekordbox_file(output_file):
            logger.info(
                f"Synchronisation terminée: {stats['tracks_updated_with_cue_points']} tracks mises à jour, "
                f"{stats['total_cue_points_added']} cue points ajoutés"
            )
        else:
            stats['success'] = False
            stats['error'] = 'Erreur lors de la sauvegarde'

        return stats

    def _initialize_stats(self) -> dict:
        return {
            'success': True,
            'total_tracks_in_rekordbox_file': 0,
            'rubitrack_tracks_processed': 0,
            'tracks_found_and_matched': 0,
            'tracks_updated_with_cue_points': 0,
            'total_cue_points_added': 0,
            'unmatched_rekordbox_tracks': []
        }

    def _get_rubitrack_tracks(self) -> Iterable[Track]:
        return Track.objects.filter(
            cue_points__isnull=False
        ).select_related('artist').prefetch_related('cue_points')

    def _build_rubitrack_lookup(self, rubitrack_tracks: Iterable[Track]) -> Dict[str, Dict[str, Union[str, Track]]]:
        lookup: Dict[str, Dict[str, Union[str, Track]]] = {}
        for track in rubitrack_tracks:
            artist_name = self._normalize_text(track.artist.name) if track.artist else ''
            title = self._normalize_text(track.title)
            key = f"{artist_name.lower()}|{title.lower()}"
            item: Dict[str, Union[str, Track]] = {
                'track': track,
                'file_path': self._normalize_traktor_path(track.file_path),
            }
            if key in lookup:
                # Deux tracks Rubitrack se normalisent vers la même clé: on garde
                # la première (first-wins) pour rester déterministe
                logger.warning(
                    "Collision de clé de matching '%s': '%s' ignorée, '%s' conservée",
                    key, track.title, lookup[key]['track'].title,
                )
            else:
                lookup[key] = item
            path_key = f"path|{item['file_path']}"
            if item['file_path'] and path_key not in lookup:
                lookup[path_key] = item
        return lookup

    def _process_tracks(self, rubitrack_tracks, collection, stats, mode, rubitrack_lookup):
        for rekordbox_track in collection.findall('TRACK'):
            # Dans un XML Rekordbox, la localisation est l'attribut Location
            # du TRACK (URI file://localhost/...), pas un élément enfant
            rb_path = self._normalize_rekordbox_location(rekordbox_track.get('Location', ''))
            # Skip Rekordbox sampler content
            if '/rekordbox/sampler/' in rb_path:
                # do not count as unmatched or processed
                continue
            rb_artist = self._normalize_text(rekordbox_track.get('Artist', '')).lower()
            rb_title = self._normalize_text(rekordbox_track.get('Name', '')).lower()
            key = f"{rb_artist}|{rb_title}"
            item = rubitrack_lookup.get(key)
            if not item and rb_path:
                # Fallback: match par chemin de fichier
                item = rubitrack_lookup.get(f"path|{rb_path}")
            if item:
                stats['tracks_found_and_matched'] += 1
                try:
                    self._update_track(rekordbox_track, item['track'], mode, stats)
                except Exception as e:
                    logger.error(f"Erreur lors du traitement de {item['track'].title}: {e}")
            else:
                stats['unmatched_rekordbox_tracks'].append({
                    'title': rekordbox_track.get('Name', '').strip(),
                    'artist': rekordbox_track.get('Artist', '').strip()
                })

    def _update_track(self, rekordbox_track, rubitrack_track, mode, stats):
        if mode == 'overwrite':
            self.remove_existing_cue_points(rekordbox_track)
        elif mode == 'add_only':
            # Ne supprime que nos marqueurs RCue*
            self.remove_system_generated_cue_points(rekordbox_track)

        track_cue_points = rubitrack_track.cue_points
        cue_points_added = 0
        # Ne PAS compacter: respecter les indices d'origine 1..8
        for i in range(1, 9):
            cue_point_obj = getattr(track_cue_points, f'cue_point_{i}', None)
            if not cue_point_obj:
                continue

            # Déterminer le type Traktor du cue (0=hot, 4=grid/loop) pour refléter exactement dans Rekordbox
            # traktor_type est un CharField: comparer en str
            traktor_type = getattr(cue_point_obj, 'traktor_type', None)
            is_type4 = (str(traktor_type) == '4')

            # Calcul en Decimal pour conserver la précision Traktor
            try:
                time_ms_val = getattr(cue_point_obj, 'time_ms', None)
                if time_ms_val is not None:
                    start_ms_dec = Decimal(str(time_ms_val))
                else:
                    sec = self.parse_time_to_seconds(cue_point_obj.time)
                    start_ms_dec = Decimal(str(sec)) * Decimal('1000')
            except (InvalidOperation, ValueError, TypeError) as e:
                logger.error(f"Conversion temps échouée pour cue {i}: {e}")
                continue

            time_seconds_dec = start_ms_dec / Decimal('1000')
            name = f'RCue{i}'

            # Traiter tous les cues comme hot cues: Num pour 1..3, sinon -1
            base_num_value = (i - 1) if (i <= 3) else -1

            time_seconds_float = float(time_seconds_dec)

            if mode == 'add_only':
                # Si un pad 0..2 est déjà occupé (Type 0 ou 4 avec Num), ne pas toucher: ne rien ajouter pour cet index
                if base_num_value in (0, 1, 2) and self._hot_cue_exists(rekordbox_track, base_num_value):
                    continue
                # Ne pas créer de doublon si un marqueur existe déjà très proche de la position
                if self._has_existing_cue_near_start(rekordbox_track, time_seconds_float, CUE_POINT_IDENTICAL_START_TIME_DIFF_MS):
                    continue
            # Calcul d'une éventuelle loop via LEN/duration
            end_seconds_dec: Optional[Decimal] = None
            len_ms_val = getattr(cue_point_obj, 'len_ms', None)
            loop_len_ms_dec: Optional[Decimal] = None
            if len_ms_val is not None:
                try:
                    loop_len_ms_dec = Decimal(str(len_ms_val))
                except (InvalidOperation, ValueError):
                    loop_len_ms_dec = None
            else:
                duration_attr = getattr(cue_point_obj, 'duration', None)
                if duration_attr is not None:
                    try:
                        loop_len_ms_dec = Decimal(str(duration_attr)) * Decimal('1000')
                    except (InvalidOperation, ValueError):
                        loop_len_ms_dec = None
            if loop_len_ms_dec and loop_len_ms_dec > 0:
                end_seconds_dec = (start_ms_dec + loop_len_ms_dec) / Decimal('1000')

            # Pour les cue points 4-8, si traktor_type=4 (loop), créer comme Type 4 dans Rekordbox
            force_loop = False
            if i > 3 and is_type4:
                force_loop = True

            self.add_cue_point_to_track(
                rekordbox_track,
                time_seconds_float,
                name,
                base_num_value,
                float(end_seconds_dec) if end_seconds_dec is not None else None,
                force_loop=force_loop,
            )
            cue_points_added += 1
        if cue_points_added > 0:
            stats['tracks_updated_with_cue_points'] += 1
            stats['total_cue_points_added'] += cue_points_added

    def parse_time_to_seconds(self, time_str: str) -> float:
        """
        Convertit le temps en secondes pour Rekordbox.
        Accepte:
        - Format "MM:SS" (ex: "1:05" -> 65.0)
        - Valeur Traktor brute en millisecondes (ex: "29801.179384" -> 29.801179)
        - Valeur en secondes (ex: "29.801" -> 29.801)
        """
        try:
            if isinstance(time_str, (int, float)):
                # Numérique direct: si valeur > 1000, probablement millisecondes
                val = float(time_str)
                return val / 1000.0 if val > 1000 else val
            s = str(time_str).strip()
            if ':' in s:
                # MM:SS
                parts = s.split(':')
                if len(parts) == 2:
                    minutes = int(parts[0])
                    seconds = float(parts[1])
                    return minutes * 60 + seconds
            # Sinon, nombre simple: ms ou s
            val = float(s)
            return val / 1000.0 if val > 1000 else val
        except (ValueError, TypeError):
            logger.error(f"Invalid time value: {time_str}")
            return 0.0


def synchronize_rekordbox_collection(
    input_file: str,
    output_file: Optional[str] = None,
    mode: str = 'overwrite'
) -> dict:
    """
    Fonction utilitaire pour synchroniser les cue points vers Rekordbox

    Args:
        input_file (str): Fichier collection.xml Rekordbox d'entrée
        output_file (str, optional): Fichier de sortie (si None, remplace l'original)
        mode (str, optional): Mode de synchronisation ('overwrite' ou 'add_only')

    Returns:
        dict: Statistiques de l'opération
        
    Usage:
        from track.collection.rekordbox.synchronize_rekordbox_collection import synchronize_rekordbox_collection
        
        stats = synchronize_rekordbox_collection(
            '/path/to/rekordbox_collection.xml',
            '/path/to/rekordbox_collection_updated.xml'
        )
        print(f"Résultat: {stats}")
    """
    synchronizer = RekordboxCollectionSynchronizer()
    return synchronizer.synchronize_rekordbox_collection(input_file, output_file, mode)
