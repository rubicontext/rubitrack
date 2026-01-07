"""
Module simple pour synchroniser les cue points entre Rubitrack et Rekordbox
Se concentre uniquement sur le remplacement des cue points, sans toucher aux autres données
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
from ...models import Track
import logging
from typing import Dict, Iterable, Optional, Tuple, Union
from decimal import Decimal, ROUND_HALF_UP

logger = logging.getLogger(__name__)

# Ne pas dupliquer un cue si un marqueur existe déjà à une position très proche (en add_only)
CUE_POINT_IDENTICAL_START_TIME_DIFF_MS = 100

# Mise à jour des couleurs des hot cues 1, 2, 3 pour inclure les valeurs RGB
HOT_CUE_COLORS = {
    1: {"Red": "60", "Green": "235", "Blue": "80"},  # Vert
    2: {"Red": "69", "Green": "172", "Blue": "219"},  # Bleu clair
    3: {"Red": "60", "Green": "235", "Blue": "80"}   # Vert
}


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
        except Exception as e:
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
        except Exception as e:
            logger.error(f"Erreur sauvegarde: {e}")
            return False
    
    def time_to_seconds(self, time_ms: float) -> float:
        """
        Convertit un temps en millisecondes (Traktor) en secondes (Rekordbox).
        
        Args:
            time_ms (float): Temps en millisecondes (Traktor).
        
        Returns:
            float: Temps en secondes (Rekordbox).
        """
        return time_ms / 1000

    def seconds_to_rekordbox_position(self, seconds: Union[float, Decimal]) -> str:
        """Retourne la position Rekordbox en secondes avec 3 décimales (ex: 33.000), arrondie correctement."""
        try:
            d = seconds if isinstance(seconds, Decimal) else Decimal(str(seconds))
            return f"{d.quantize(Decimal('0.000'), rounding=ROUND_HALF_UP)}"
        except Exception:
            return "0.000"
    
    def _normalize_text(self, s: str) -> str:
        """
        Normalize titles/artists to base forms:
        - Strip key/rating suffixes like " - Am - 6" or trailing " - 6"
        - Remove site watermarks and noise tokens (FREE DOWNLOAD, snippet, HD)
        - Remove bracketed/parenthetical content
        - Unicode NFKC and collapse whitespace
        """
        import re
        import unicodedata
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

    def _rb_fields(self, track: ET.Element) -> Tuple[str, str]:
        """Helper to fetch normalized Artist/Name from a Rekordbox TRACK."""
        artist = self._normalize_text(track.get('Artist', ''))
        title = self._normalize_text(track.get('Name', ''))
        return artist, title

    def find_track_element(self, artist_name: str, track_title: str) -> Optional[ET.Element]:
        """
        Trouve un élément TRACK dans la collection Rekordbox avec recherche intelligente
        
        Stratégie de recherche :
        1. Match exact (artist + title)
        2. Match avec normalisation des espaces (supprime espaces en trop)
        3. Match avec artist sans espaces vs artist avec espaces en base
        4. Fallback par file path ou Audio ID si présents
        
        Args:
            artist_name (str): Nom de l'artiste
            track_title (str): Titre de la track
            
        Returns:
            ET.Element: Élément TRACK trouvé ou None
        """
        if not self.root:
            return None
        collection = self.root.find('.//COLLECTION')
        if collection is None:
            return None
        artist_clean = self._normalize_text(artist_name or '')
        title_clean = self._normalize_text(track_title or '')
        # Étape 1: Match exact (normalized)
        for track in collection.findall('TRACK'):
            rb_artist, rb_title = self._rb_fields(track)
            if rb_artist.lower() == artist_clean.lower() and rb_title.lower() == title_clean.lower():
                return track
        # Étape 2: Normalisation espaces multiples
        artist_normalized = ' '.join(artist_clean.split())
        title_normalized = ' '.join(title_clean.split())
        for track in collection.findall('TRACK'):
            rb_artist = ' '.join(self._normalize_text(track.get('Artist', '')).split())
            rb_title = ' '.join(self._normalize_text(track.get('Name', '')).split())
            if rb_artist.lower() == artist_normalized.lower() and rb_title.lower() == title_normalized.lower():
                logger.debug("Match normalisé: '%s' / '%s'", rb_artist, rb_title)
                return track
        # Étape 3: Sans espaces côté artist
        artist_no_spaces = artist_clean.replace(' ', '')
        for track in collection.findall('TRACK'):
            rb_artist, rb_title = self._rb_fields(track)
            cond_artist = rb_artist.replace(' ', '').lower() == artist_no_spaces.lower()
            cond_title = rb_title.lower() == title_clean.lower()
            if cond_artist and cond_title:
                logger.debug(
                    "Match sans espaces: '%s' → '%s' (titre: %s)",
                    rb_artist,
                    artist_clean,
                    track_title,
                )
                return track
        return None

    def remove_existing_cue_points(self, track_element: ET.Element) -> None:
        """
        Supprime tous les cue points existants d'une track

        Args:
            track_element (ET.Element): Élément TRACK
        """
        # Supprimer tous les éléments POSITION_MARK (cue points)
        for position_mark in track_element.findall('POSITION_MARK'):
            track_element.remove(position_mark)
    
    def remove_program_generated_cue_points(self, track_element: ET.Element, mode: str) -> None:
        """
        Supprime uniquement les cue points générés par le programme.
        - RCue X (1..8) dans tous les modes
        - A, B, C (slots 1..3) si en mode add_only (permet la mise à jour)
        Conserve les autres (loops, memory cues, cues manuels).
        
        Args:
            track_element (ET.Element): Élément TRACK
            mode (str): Mode de synchronisation ('overwrite', 'preserve', 'add_only')
        """
        program_names = set()
        for i in range(1, 9):
            program_names.add(f"RCue{i}")          # new format
            program_names.add(f"RCue {i}")        # legacy format with space
        # legacy A,B,C hot cue names from previous version
        program_names.update({'A', 'B', 'C'})
        for pm in list(track_element.findall('POSITION_MARK')):
            try:
                if pm.get('Type') == '0':
                    name = pm.get('Name', '')
                    if name in program_names:
                        track_element.remove(pm)
            except Exception:
                continue
    
    def add_cue_point_to_track(
        self,
        track_element: ET.Element,
        cue_number: int,
        time_seconds: float,
        name: str,
        num_value: int,
        end_seconds: Optional[float] = None,
    ) -> None:
        """
        Ajoute un cue point à une track Rekordbox.
        - Si end_seconds est fourni et > start: export en loop (Type 4) avec End et couleurs orange.
          Si un num_value (0..2) est fourni, on positionne aussi Num pour créer une "loop hot cue" (supporté par Rekordbox).
        - Sinon: export en hot cue (Type 0) avec Num et couleurs vertes.
        """
        position_mark = ET.SubElement(track_element, 'POSITION_MARK')
        position_mark.set('Name', name)
        start_value = self.seconds_to_rekordbox_position(time_seconds)
        position_mark.set('Start', start_value)
        if end_seconds is not None and end_seconds > time_seconds:
            # Loop (Type 4) avec End et couleur orange
            end_value = self.seconds_to_rekordbox_position(end_seconds)
            position_mark.set('Type', '4')
            position_mark.set('End', end_value)
            # S'il s'agit d'un slot hot (0..2), renseigner Num pour qu'elle apparaisse sur le pad correspondant
            if num_value != -1:
                position_mark.set('Num', str(num_value))
            position_mark.set('Red', '255')
            position_mark.set('Green', '140')
            position_mark.set('Blue', '0')
            logger.debug("Add LOOP POSITION_MARK: start=%s end=%s num=%s", start_value, end_value, (str(num_value) if num_value != -1 else ''))
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
            try:
                name = pm.get('Name', '')
                pm_type = pm.get('Type')
                if name.startswith('RCue'):
                    track_element.remove(pm)
                    logger.debug(f"Supprimé cue point système (RCue*): {name}")
                elif pm_type == '0' and name in {'A', 'B', 'C'}:
                    track_element.remove(pm)
                    logger.debug(f"Supprimé cue point système legacy: {name}")
            except Exception:
                continue

    def _hot_cue_exists(self, track_element: ET.Element, num: int) -> bool:  # type: ignore[override]
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
    
    def _memory_cue_at_start_exists(
        self,  # type: ignore[override]
        track_element: ET.Element,
        start_seconds: float
    ) -> bool:  # type: ignore[override]
        target = self.seconds_to_rekordbox_position(start_seconds)
        for pm in track_element.findall('POSITION_MARK'):
            if pm.get('Start') == target:
                return True
        return False
    
    def _has_existing_cue_near_start(self, track_element: ET.Element, start_seconds: float, diff_ms: int) -> bool:
        """Retourne True si un POSITION_MARK non-RCue existe à +/- diff_ms autour de start_seconds.
        Les marqueurs nommés 'RCue*' ne bloquent pas l'ajout en add_only.
        """
        try:
            delta = Decimal(str(diff_ms)) / Decimal('1000')
            target = Decimal(str(start_seconds))
        except Exception:
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
            except Exception:
                continue
            if (target - s_dec).copy_abs() <= delta:
                return True
        return False
    
    def synchronize_rekordbox_collection(
        self,  # type: ignore[override]
        input_file: str,
        output_file: Optional[str] = None,
        overwrite_existing: bool = True,
        mode: Optional[str] = None
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
            overwrite_existing (bool, optional): Contrôle la suppression des cue points existants
            mode (str, optional): Mode de synchronisation ('overwrite', 'add_only')
            
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
                'file_path': (track.file_path or '').lower(),
                'audio_id': (track.audio_id or '').lower(),
            }
            lookup[key] = item
            if item['file_path']:
                lookup[f"path|{item['file_path']}"] = item
            if item['audio_id']:
                lookup[f"audio|{item['audio_id']}"] = item
        return lookup

    def _process_tracks(self, rubitrack_tracks, collection, stats, mode, rubitrack_lookup):
        for rekordbox_track in collection.findall('TRACK'):
            # Skip Rekordbox sampler content
            rb_path = ''
            loc = rekordbox_track.find('LOCATION')
            if loc is not None:
                rb_file = (loc.get('FILE') or '').lower()
                rb_dir = (loc.get('DIR') or '').lower()
                rb_vol = (loc.get('VOLUME') or '').lower()
                rb_path = f"{rb_vol}{rb_dir}{rb_file}"
                if '/rekordbox/sampler/' in rb_path:
                    # do not count as unmatched or processed
                    continue
            rb_artist = self._normalize_text(rekordbox_track.get('Artist', '')).lower()
            rb_title = self._normalize_text(rekordbox_track.get('Name', '')).lower()
            key = f"{rb_artist}|{rb_title}"
            item = rubitrack_lookup.get(key)
            if not item:
                # try path / audio id fallback
                audio_id = (rekordbox_track.get('AudioId') or '').lower()
                path_key = f"path|{rb_path}" if rb_path else None
                item = (rubitrack_lookup.get(path_key) if path_key else None) or rubitrack_lookup.get(f"audio|{audio_id}")
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
            traktor_type = getattr(cue_point_obj, 'traktor_type', None)
            is_type4 = (traktor_type == 4)

            # Calcul en Decimal pour conserver la précision Traktor
            try:
                time_ms_val = getattr(cue_point_obj, 'time_ms', None)
                if time_ms_val is not None:
                    start_ms_dec = Decimal(str(time_ms_val))
                else:
                    sec = self.parse_time_to_seconds(cue_point_obj.time)
                    start_ms_dec = Decimal(str(sec)) * Decimal('1000')
            except Exception as e:
                logger.error(f"Conversion temps échouée pour cue {i}: {e}")
                continue

            time_seconds_dec = start_ms_dec / Decimal('1000')
            name = f'RCue{i}'

            # Traiter tous les cues comme hot cues: Num pour 1..3, sinon -1
            base_num_value = (i - 1) if (i <= 3) else -1

            time_seconds_float = float(time_seconds_dec)
            final_num_value = base_num_value

            if mode == 'add_only':
                # Si un pad 0..2 est déjà occupé (Type 0 ou 4 avec Num), ne pas toucher: ne rien ajouter pour cet index
                if base_num_value in (0, 1, 2) and self._hot_cue_exists(rekordbox_track, base_num_value):
                    continue
                # Ne pas créer de doublon si un marqueur existe déjà très proche de la position
                if self._has_existing_cue_near_start(rekordbox_track, time_seconds_float, CUE_POINT_IDENTICAL_START_TIME_DIFF_MS):
                    continue
                if final_num_value != -1 and self._hot_cue_exists(rekordbox_track, final_num_value):
                    final_num_value = -1
                # Ne pas dédupliquer: conserver les existants
            # Calcul d'une éventuelle loop via LEN/duration
            end_seconds_dec: Optional[Decimal] = None
            len_ms_val = getattr(cue_point_obj, 'len_ms', None)
            loop_len_ms_dec: Optional[Decimal] = None
            if len_ms_val is not None:
                try:
                    loop_len_ms_dec = Decimal(str(len_ms_val))
                except Exception:
                    loop_len_ms_dec = None
            else:
                duration_attr = getattr(cue_point_obj, 'duration', None)
                if duration_attr is not None:
                    try:
                        loop_len_ms_dec = Decimal(str(duration_attr)) * Decimal('1000')
                    except Exception:
                        loop_len_ms_dec = None
            if loop_len_ms_dec and loop_len_ms_dec > 0:
                end_seconds_dec = (start_ms_dec + loop_len_ms_dec) / Decimal('1000')

            self.add_cue_point_to_track(
                rekordbox_track,
                i,
                time_seconds_float,
                name,
                final_num_value,
                float(end_seconds_dec) if end_seconds_dec is not None else None,
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
        except Exception:
            logger.error(f"Invalid time value: {time_str}")
            return 0.0


def synchronize_rekordbox_collection(
    input_file: str,
    output_file: Optional[str] = None,
    overwrite_existing: bool = True,
    mode: Optional[str] = None
) -> dict:
    """
    Fonction utilitaire pour synchroniser les cue points vers Rekordbox
    
    Args:
        input_file (str): Fichier collection.xml Rekordbox d'entrée
        output_file (str, optional): Fichier de sortie (si None, remplace l'original)
        overwrite_existing (bool, optional): Contrôle la suppression des cue points existants
        mode (str, optional): Mode de synchronisation ('overwrite', 'preserve', 'add_only')
        
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
    return synchronizer.synchronize_rekordbox_collection(input_file, output_file, overwrite_existing, mode)
