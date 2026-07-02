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

from rapidfuzz import fuzz, process as fuzz_process

from ...models import Playlist, Track

logger = logging.getLogger(__name__)

# Ne pas dupliquer un cue si un marqueur existe déjà à une position très proche (en add_only)
CUE_POINT_IDENTICAL_START_TIME_DIFF_MS = 100

# Rejeter un match titre/artiste si les durées divergent de plus de N secondes
DURATION_MISMATCH_TOLERANCE_SECONDS = 5

# Score minimal (0-100) pour proposer un match approximatif dans le rapport.
# Les suggestions ne sont JAMAIS appliquées au XML: elles sont à confirmer à la main.
FUZZY_MATCH_MIN_SCORE = 85
FUZZY_MATCH_CANDIDATES = 3


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
        mode: str = 'overwrite',
        export_playlists: bool = True,
    ) -> dict:
        """
        Synchronise Rubitrack vers Rekordbox: cue points, beatgrid (ancre TEMPO),
        métadonnées manquantes (Rating/Tonality/Comments/PlayCount/Genre) et
        playlists (dossier 'Rubitrack' dans le nœud PLAYLISTS).
        Modes:
          overwrite : supprime tous les cue points existants puis ajoute tous les RCue1-8
          add_only  : supprime uniquement les cue points système générés (RCueX), préserve les cue points manuels,
                     puis ajoute conditionnellement les nouveaux (slots libres pour 1-3, positions libres pour 4-8)

        Args:
            input_file (str): Fichier Rekordbox d'entrée
            output_file (str, optional): Fichier de sortie (si None, remplace l'original)
            mode (str, optional): Mode de synchronisation ('overwrite' ou 'add_only')
            export_playlists (bool, optional): Exporte les playlists Rubitrack dans le XML

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
        matched_track_keys = self._process_tracks(rubitrack_tracks, collection, stats, mode, rubitrack_lookup)

        if export_playlists:
            self._export_playlists(matched_track_keys, stats)

        if self.save_rekordbox_file(output_file):
            logger.info(
                f"Synchronisation terminée: {stats['tracks_updated_with_cue_points']} tracks mises à jour, "
                f"{stats['total_cue_points_added']} cue points ajoutés"
            )
        else:
            stats['success'] = False
            stats['error'] = 'Erreur lors de la sauvegarde'

        return stats

    def _export_playlists(self, matched_track_keys: Dict[int, str], stats: dict) -> None:
        """Exporte les playlists Rubitrack dans le nœud PLAYLISTS du XML, sous un
        dossier 'Rubitrack' (recréé à chaque sync: idempotent, ne touche pas aux
        autres playlists Rekordbox). Seules les tracks matchées sont référencées
        (TRACK Key = TrackID, KeyType 0)."""
        playlists_node = self.root.find('PLAYLISTS')
        if playlists_node is None:
            playlists_node = ET.SubElement(self.root, 'PLAYLISTS')
        root_node = None
        for node in playlists_node.findall('NODE'):
            if node.get('Name') == 'ROOT' or node.get('Type') == '0':
                root_node = node
                break
        if root_node is None:
            root_node = ET.SubElement(playlists_node, 'NODE', {'Type': '0', 'Name': 'ROOT', 'Count': '0'})

        # Idempotence: retirer le dossier Rubitrack d'une sync précédente
        for child in list(root_node.findall('NODE')):
            if child.get('Name') == 'Rubitrack' and child.get('Type') == '0':
                root_node.remove(child)

        folder = ET.SubElement(root_node, 'NODE', {'Name': 'Rubitrack', 'Type': '0', 'Count': '0'})
        exported = 0
        for playlist in Playlist.objects.order_by('rank', '-id'):
            keys = [
                matched_track_keys[track_id]
                for track_id in playlist.get_ordered_track_ids()
                if track_id in matched_track_keys
            ]
            if not keys:
                continue
            playlist_node = ET.SubElement(folder, 'NODE', {
                'Name': playlist.name,
                'Type': '1',
                'KeyType': '0',
                'Entries': str(len(keys)),
            })
            for key in keys:
                ET.SubElement(playlist_node, 'TRACK', {'Key': key})
            exported += 1
            stats['playlist_entries_exported'] += len(keys)

        folder.set('Count', str(exported))
        root_node.set('Count', str(len(root_node.findall('NODE'))))
        stats['playlists_exported'] = exported
        if exported:
            logger.info("Playlists exportées vers Rekordbox: %s", exported)

    def _initialize_stats(self) -> dict:
        return {
            'success': True,
            'total_tracks_in_rekordbox_file': 0,
            'rubitrack_tracks_processed': 0,
            'tracks_found_and_matched': 0,
            'tracks_updated_with_cue_points': 0,
            'total_cue_points_added': 0,
            'beatgrids_written': 0,
            'metadata_fields_filled': 0,
            'playlists_exported': 0,
            'playlist_entries_exported': 0,
            'fuzzy_candidates_found': 0,
            'unmatched_rekordbox_tracks': []
        }

    def _get_rubitrack_tracks(self) -> Iterable[Track]:
        return Track.objects.filter(
            cue_points__isnull=False
        ).distinct().select_related('artist').prefetch_related('cue_points')

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

    def _duration_mismatch(self, rubitrack_track, rekordbox_track) -> bool:
        """True si les durées connues des deux côtés divergent au-delà de la
        tolérance — garde-fou contre les faux matchs titre/artiste
        (ex: radio edit vs extended mix)."""
        playtime = rubitrack_track.playtime
        total_time = rekordbox_track.get('TotalTime')
        if not playtime or not total_time:
            return False
        try:
            total_seconds = float(total_time)
        except ValueError:
            return False
        return abs(float(playtime) - total_seconds) > DURATION_MISMATCH_TOLERANCE_SECONDS

    def _build_fuzzy_choices(self, rubitrack_tracks) -> Dict[str, Track]:
        """Chaînes normalisées 'artist title' -> track, pour le fuzzy matching."""
        choices: Dict[str, Track] = {}
        for track in rubitrack_tracks:
            artist_name = self._normalize_text(track.artist.name) if track.artist else ''
            title = self._normalize_text(track.title)
            choices.setdefault(f"{artist_name} {title}".lower().strip(), track)
        return choices

    def _find_fuzzy_suggestion(self, rb_artist: str, rb_title: str,
                               rekordbox_track, fuzzy_choices: Dict[str, Track]):
        """Cherche un candidat approximatif (suggestion pour le rapport, jamais
        appliqué). Retourne (track, score) ou None. Les candidats dont la durée
        diverge sont écartés (même garde-fou que le matching exact)."""
        if not fuzzy_choices:
            return None
        query = f"{rb_artist} {rb_title}".strip()
        if not query:
            return None
        results = fuzz_process.extract(
            query,
            fuzzy_choices.keys(),
            scorer=fuzz.token_sort_ratio,
            score_cutoff=FUZZY_MATCH_MIN_SCORE,
            limit=FUZZY_MATCH_CANDIDATES,
        )
        for choice, score, _ in results:
            candidate = fuzzy_choices[choice]
            if not self._duration_mismatch(candidate, rekordbox_track):
                return candidate, round(score)
        return None

    def _process_tracks(self, rubitrack_tracks, collection, stats, mode, rubitrack_lookup):
        # rubitrack track id -> TrackID Rekordbox, pour l'export des playlists
        matched_track_keys: Dict[int, str] = {}
        fuzzy_choices = self._build_fuzzy_choices(rubitrack_tracks)
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
            unmatched_reason = 'no_match'
            item = rubitrack_lookup.get(key)
            if item and self._duration_mismatch(item['track'], rekordbox_track):
                logger.info(
                    "Match titre/artiste rejeté (durées divergentes): '%s' (%ss vs %ss)",
                    rekordbox_track.get('Name', ''),
                    rekordbox_track.get('TotalTime'),
                    item['track'].playtime,
                )
                item = None
                unmatched_reason = 'duration_mismatch'
            if not item and rb_path:
                # Fallback: match par chemin de fichier (preuve forte, pas de garde-fou durée)
                item = rubitrack_lookup.get(f"path|{rb_path}")
            if item:
                stats['tracks_found_and_matched'] += 1
                track_id_attr = rekordbox_track.get('TrackID')
                if track_id_attr:
                    matched_track_keys[item['track'].id] = track_id_attr
                try:
                    self._update_track(rekordbox_track, item['track'], mode, stats)
                except Exception as e:
                    logger.error(f"Erreur lors du traitement de {item['track'].title}: {e}")
            else:
                entry = {
                    'title': rekordbox_track.get('Name', '').strip(),
                    'artist': rekordbox_track.get('Artist', '').strip(),
                    'location': rekordbox_track.get('Location', ''),
                    'reason': unmatched_reason,
                    'suggested_match': '',
                    'match_score': '',
                }
                suggestion = self._find_fuzzy_suggestion(
                    rb_artist, rb_title, rekordbox_track, fuzzy_choices
                )
                if suggestion:
                    candidate, score = suggestion
                    artist_name = candidate.artist.name if candidate.artist else ''
                    entry['suggested_match'] = f"{artist_name} - {candidate.title}".strip(' -')
                    entry['match_score'] = score
                    stats['fuzzy_candidates_found'] += 1
                    logger.info(
                        "Suggestion approximative: '%s - %s' ~ '%s' (score %s)",
                        entry['artist'], entry['title'], entry['suggested_match'], score,
                    )
                stats['unmatched_rekordbox_tracks'].append(entry)
        return matched_track_keys

    def _sync_beatgrid(self, rekordbox_track, rubitrack_track, cue_points_by_slot, mode, stats):
        """Écrit l'ancre de beatgrid Rekordbox (TEMPO Inizio/Bpm) depuis le cue
        grid Traktor (traktor_type=4) et le BPM de la track.
        - overwrite : remplace les TEMPO existants
        - add_only  : n'écrit que si aucun TEMPO n'existe
        Sans grid Traktor ou sans BPM, les TEMPO existants sont préservés."""
        grid_cues = [
            cp for cp in cue_points_by_slot.values()
            if str(cp.traktor_type) == '4' and cp.time_ms is not None
        ]
        if not grid_cues or not rubitrack_track.bpm:
            return
        existing_tempos = rekordbox_track.findall('TEMPO')
        if mode == 'add_only' and existing_tempos:
            return
        for tempo in existing_tempos:
            rekordbox_track.remove(tempo)

        anchor = min(grid_cues, key=lambda cp: cp.time_ms)
        tempo = ET.Element('TEMPO')
        tempo.set('Inizio', self.seconds_to_rekordbox_position(Decimal(str(anchor.time_ms)) / Decimal('1000')))
        tempo.set('Bpm', f"{float(rubitrack_track.bpm):.2f}")
        tempo.set('Metro', '4/4')
        tempo.set('Battito', '1')
        # Convention Rekordbox: TEMPO avant les POSITION_MARK
        children = list(rekordbox_track)
        insert_at = next(
            (i for i, child in enumerate(children) if child.tag == 'POSITION_MARK'),
            len(children),
        )
        rekordbox_track.insert(insert_at, tempo)
        stats['beatgrids_written'] += 1

    # Attributs Rekordbox complétés depuis Rubitrack quand ils sont vides
    # (valeur '0' considérée comme vide pour Rating/PlayCount)
    METADATA_EMPTY_VALUES = {'Rating': {'', '0'}, 'PlayCount': {'', '0'}}

    def _fill_missing_metadata(self, rekordbox_track, rubitrack_track, stats):
        """Complète les métadonnées Rekordbox manquantes depuis Rubitrack,
        sans jamais écraser une valeur déjà présente."""
        candidates = {
            'Rating': str(rubitrack_track.ranking * 51) if rubitrack_track.ranking else None,
            'Tonality': rubitrack_track.musical_key or None,
            'Comments': rubitrack_track.comment or None,
            'PlayCount': str(rubitrack_track.playcount) if rubitrack_track.playcount else None,
            'Genre': rubitrack_track.genre.name if rubitrack_track.genre else None,
        }
        for attr, value in candidates.items():
            if value is None:
                continue
            current = (rekordbox_track.get(attr) or '').strip()
            empty_values = self.METADATA_EMPTY_VALUES.get(attr, {''})
            if current in empty_values:
                rekordbox_track.set(attr, value)
                stats['metadata_fields_filled'] += 1

    def _update_track(self, rekordbox_track, rubitrack_track, mode, stats):
        if mode == 'overwrite':
            self.remove_existing_cue_points(rekordbox_track)
        elif mode == 'add_only':
            # Ne supprime que nos marqueurs RCue*
            self.remove_system_generated_cue_points(rekordbox_track)

        cue_points_by_slot = {cp.slot: cp for cp in rubitrack_track.cue_points.all()}
        self._sync_beatgrid(rekordbox_track, rubitrack_track, cue_points_by_slot, mode, stats)
        self._fill_missing_metadata(rekordbox_track, rubitrack_track, stats)
        cue_points_added = 0
        # Ne PAS compacter: respecter les indices d'origine 1..8
        for i in range(1, 9):
            cue_point_obj = cue_points_by_slot.get(i)
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
    mode: str = 'overwrite',
    export_playlists: bool = True,
) -> dict:
    """
    Fonction utilitaire pour synchroniser Rubitrack vers Rekordbox
    (cue points, beatgrid, métadonnées manquantes, playlists)

    Args:
        input_file (str): Fichier collection.xml Rekordbox d'entrée
        output_file (str, optional): Fichier de sortie (si None, remplace l'original)
        mode (str, optional): Mode de synchronisation ('overwrite' ou 'add_only')
        export_playlists (bool, optional): Exporte les playlists Rubitrack dans le XML

    Returns:
        dict: Statistiques de l'opération

    Usage:
        from track.collection.rekordbox.synchronize_rekordbox_collection import synchronize_rekordbox_collection

        stats = synchronize_rekordbox_collection(
            '/path/to/rekordbox_collection.xml',
            '/path/to/rekordbox_collection_updated.xml'
        )
    """
    synchronizer = RekordboxCollectionSynchronizer()
    return synchronizer.synchronize_rekordbox_collection(input_file, output_file, mode, export_playlists)
