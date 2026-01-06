"""
Utilitaires pour la gestion et conversion des tonalités musicales (musical keys)
Supporte les conversions entre notation Camelot Wheel, Open Key et notation musicale traditionnelle
"""

import re
from typing import Optional, Tuple


# Correspondance Camelot Wheel vers notation musicale traditionnelle
CAMELOT_TO_MUSICAL = {
    # Majeurs
    '1B': 'B', '2B': 'F#', '3B': 'Db', '4B': 'Ab', '5B': 'Eb', '6B': 'Bb',
    '7B': 'F', '8B': 'C', '9B': 'G', '10B': 'D', '11B': 'A', '12B': 'E',
    
    # Mineurs
    '1A': 'Abm', '2A': 'Ebm', '3A': 'Bbm', '4A': 'Fm', '5A': 'Cm', '6A': 'Gm',
    '7A': 'Dm', '8A': 'Am', '9A': 'Em', '10A': 'Bm', '11A': 'F#m', '12A': 'C#m'
}

# Correspondance Open Key vers notation musicale traditionnelle  
OPEN_KEY_TO_MUSICAL = {
    # Majeurs (d = dur = majeur)
    '1d': 'B', '2d': 'F#', '3d': 'Db', '4d': 'Ab', '5d': 'Eb', '6d': 'Bb',
    '7d': 'F', '8d': 'C', '9d': 'G', '10d': 'D', '11d': 'A', '12d': 'E',
    
    # Mineurs (m = moll = mineur)
    '1m': 'Abm', '2m': 'Ebm', '3m': 'Bbm', '4m': 'Fm', '5m': 'Cm', '6m': 'Gm',
    '7m': 'Dm', '8m': 'Am', '9m': 'Em', '10m': 'Bm', '11m': 'F#m', '12m': 'C#m'
}

# Correspondance inverse pour reconnaître les tonalités musicales
MUSICAL_TO_CAMELOT = {v: k for k, v in CAMELOT_TO_MUSICAL.items()}
MUSICAL_TO_OPEN_KEY = {v: k for k, v in OPEN_KEY_TO_MUSICAL.items()}


def normalize_musical_key_notation(key_string: str) -> Optional[str]:
    """
    Normalise une notation de tonalité vers la notation musicale traditionnelle.
    
    Args:
        key_string: Chaîne contenant une tonalité (ex: "G#m", "10A", "6m")
        
    Returns:
        Notation musicale normalisée (ex: "G#m", "F") ou None si non trouvé
    """
    if not key_string:
        return None
        
    # Nettoyer la chaîne
    key_string = key_string.strip()
    
    # Déjà en notation musicale traditionnelle ?
    if is_traditional_musical_notation(key_string):
        return standardize_traditional_notation(key_string)
    
    # Essayer la notation Camelot (ex: "10A", "12B")
    camelot_match = re.search(r'\b(\d{1,2}[AB])\b', key_string, re.IGNORECASE)
    if camelot_match:
        camelot_key = camelot_match.group(1).upper()
        return CAMELOT_TO_MUSICAL.get(camelot_key)
    
    # Essayer la notation Open Key (ex: "6m", "10d")
    open_key_match = re.search(r'\b(\d{1,2}[md])\b', key_string, re.IGNORECASE)
    if open_key_match:
        open_key = open_key_match.group(1).lower()
        return OPEN_KEY_TO_MUSICAL.get(open_key)
    
    return None


def is_traditional_musical_notation(key_string: str) -> bool:
    """
    Vérifie si une chaîne est déjà en notation musicale traditionnelle.
    
    Args:
        key_string: Chaîne à vérifier
        
    Returns:
        True si c'est déjà de la notation musicale traditionnelle
    """
    # Pattern pour notation musicale : C, C#, C♯, Db, D♭, Fm, G#m, G♯m, etc.
    musical_pattern = r'^[A-G][#♯b♭]?m?$'
    return bool(re.match(musical_pattern, key_string.strip(), re.IGNORECASE))


def standardize_traditional_notation(key_string: str) -> str:
    """
    Standardise une notation musicale traditionnelle (capitalisation, etc.)
    Convertit les caractères Unicode ♯/♭ en ASCII #/b
    
    Args:
        key_string: Notation musicale à standardiser
        
    Returns:
        Notation standardisée avec # et b ASCII
    """
    key_string = key_string.strip()
    
    # Convertir les caractères Unicode vers ASCII
    key_string = key_string.replace('♯', '#')  # Sharp Unicode -> ASCII
    key_string = key_string.replace('♭', 'b')  # Flat Unicode -> ASCII
    
    # Première lettre en majuscule
    if len(key_string) > 0:
        result = key_string[0].upper()
        
        # Ajouter le reste (dièse/bémol et m pour mineur)
        if len(key_string) > 1:
            rest = key_string[1:]
            # 'm' en minuscule pour mineur
            rest = re.sub(r'M$', 'm', rest, flags=re.IGNORECASE)
            result += rest
            
        return result
    
    return key_string


def extract_musical_key_from_filename(filename: str) -> Optional[str]:
    """
    Extrait une tonalité musicale d'un nom de fichier.
    
    Args:
        filename: Nom du fichier à analyser
        
    Returns:
        Tonalité trouvée normalisée ou None
    """
    if not filename:
        return None
    
    # Motifs pour détecter les tonalités dans les noms de fichiers
    patterns = [
        # Camelot Wheel : 1A, 12B, etc.
        r'\b([1-9]|1[0-2])[AB]\b',
        
        # Open Key : 1m, 12d, etc.
        r'\b([1-9]|1[0-2])[md]\b',
        
        # Notation traditionnelle : Am, F#, Gm, etc.
        r'\b([A-G][#♯b♭]?m?)\b',
        
        # Avec séparateurs : - Am -, _Dm_, etc.
        r'[-_\s]([A-G][#♯b♭]?m?)[-_\s]',
        
        # En fin de nom : filename_Am.mp3
        r'[-_]([A-G][#♯b♭]?m?)(?=\.[a-zA-Z0-9]+$)'
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, filename, re.IGNORECASE)
        for match in matches:
            key_candidate = match.group(1)
            normalized = normalize_musical_key_notation(key_candidate)
            if normalized:
                return normalized
    
    return None


def extract_musical_key_from_title(title: str) -> Optional[str]:
    """
    Extrait une tonalité musicale d'un titre de track.
    
    Args:
        title: Titre de la track à analyser
        
    Returns:
        Tonalité trouvée normalisée ou None
    """
    if not title:
        return None
    
    # Utiliser la même logique que pour les noms de fichiers
    # car les titres peuvent contenir des clés musicales
    return extract_musical_key_from_filename(title)


def get_conflicting_musical_keys(filename: str, db_musical_key: str) -> Tuple[Optional[str], Optional[str], bool]:
    """
    Compare la tonalité du nom de fichier avec celle en base de données.
    
    Args:
        filename: Nom du fichier
        db_musical_key: Tonalité stockée en base
        
    Returns:
        Tuple (filename_key, db_key, has_conflict)
    """
    filename_key = extract_musical_key_from_filename(filename)
    db_key = normalize_musical_key_notation(db_musical_key) if db_musical_key else None
    
    # Il y a conflit si les deux existent et sont différents
    has_conflict = (
        filename_key is not None and 
        db_key is not None and 
        filename_key != db_key
    )
    
    return filename_key, db_key, has_conflict


# Système de couleurs Traktor basé sur le Camelot Wheel
CAMELOT_COLORS = {
    '1A': {'color_hex': '#b7e07e', 'color_name': 'Vert clair'},
    '2A': {'color_hex': '#e6e87e', 'color_name': 'Jaune clair'},
    '3A': {'color_hex': '#f7f37e', 'color_name': 'Jaune'},
    '4A': {'color_hex': '#f7e1a0', 'color_name': 'Jaune pâle'},
    '5A': {'color_hex': '#f7c97e', 'color_name': 'Orange clair'},
    '6A': {'color_hex': '#f7a97e', 'color_name': 'Orange'},
    '7A': {'color_hex': '#f77e7e', 'color_name': 'Rouge'},
    '8A': {'color_hex': '#c97ef7', 'color_name': 'Mauve/Rose'},
    '9A': {'color_hex': '#7e7ef7', 'color_name': 'Violet'},
    '10A': {'color_hex': '#7ec9f7', 'color_name': 'Bleu'},
    '11A': {'color_hex': '#7ee8f7', 'color_name': 'Turquoise'},
    '12A': {'color_hex': '#b7e07e', 'color_name': 'Vert clair'},
    '1B': {'color_hex': '#b7e07e', 'color_name': 'Vert clair'},
    '2B': {'color_hex': '#e6e87e', 'color_name': 'Jaune clair'},
    '3B': {'color_hex': '#f7f37e', 'color_name': 'Jaune'},
    '4B': {'color_hex': '#f7e1a0', 'color_name': 'Jaune pâle'},
    '5B': {'color_hex': '#f7c97e', 'color_name': 'Orange clair'},
    '6B': {'color_hex': '#f7a97e', 'color_name': 'Orange'},
    '7B': {'color_hex': '#f77e7e', 'color_name': 'Rouge'},
    '8B': {'color_hex': '#c97ef7', 'color_name': 'Mauve/Rose'},
    '9B': {'color_hex': '#7e7ef7', 'color_name': 'Violet'},
    '10B': {'color_hex': '#7ec9f7', 'color_name': 'Bleu'},
    '11B': {'color_hex': '#7ee8f7', 'color_name': 'Turquoise'},
    '12B': {'color_hex': '#b7e07e', 'color_name': 'Vert clair'},
}


def get_traktor_color_from_musical_key(musical_key: str) -> Optional[dict]:
    """
    Récupère les informations de couleur Traktor pour une clé musicale.
    
    Args:
        musical_key: Clé musicale en notation traditionnelle (ex: "Am", "F#")
        
    Returns:
        Dictionnaire avec color_hex et color_name ou None
    """
    if not musical_key:
        return None
    
    # Normaliser la clé musicale
    normalized_key = normalize_musical_key_notation(musical_key)
    if not normalized_key:
        return None
    
    # Convertir vers Camelot pour obtenir la couleur
    camelot_key = MUSICAL_TO_CAMELOT.get(normalized_key)
    if not camelot_key:
        return None
    
    return CAMELOT_COLORS.get(camelot_key)


def get_musical_key_info(musical_key: str) -> Optional[dict]:
    """
    Récupère toutes les informations d'une clé musicale : couleur, Camelot, etc.
    
    Args:
        musical_key: Clé musicale en notation traditionnelle
        
    Returns:
        Dictionnaire avec toutes les informations ou None
    """
    if not musical_key:
        return None
    
    # Normaliser la clé musicale
    normalized_key = normalize_musical_key_notation(musical_key)
    if not normalized_key:
        return None
    
    # Obtenir la notation Camelot
    camelot_key = MUSICAL_TO_CAMELOT.get(normalized_key)
    if not camelot_key:
        return None
    
    # Obtenir les informations de couleur
    color_info = CAMELOT_COLORS.get(camelot_key, {})
    
    return {
        'musical_key': normalized_key,
        'camelot': camelot_key,
        'color_hex': color_info.get('color_hex'),
        'color_name': color_info.get('color_name')
    }


# Ordre des clés musicales selon Traktor (triées par couleur dans la Camelot wheel)
TRAKTOR_KEY_ORDER = [
    # Mineurs (A) - ordre par couleur
    'Am', 'Em', 'Bm', 'F#m', 'C#m', 'Abm', 'Ebm', 'Bbm', 'Fm', 'Cm', 'Gm', 'Dm',
    # Majeurs (B) - ordre par couleur  
    'C', 'G', 'D', 'A', 'E', 'B', 'F#', 'Db', 'Ab', 'Eb', 'Bb', 'F'
]

# Index mapping pour un accès rapide
TRAKTOR_KEY_INDEX = {key: index for index, key in enumerate(TRAKTOR_KEY_ORDER)}


def get_musical_key_distance(key1: str, key2: str) -> int:
    """
    Calcule la distance entre deux clés musicales selon l'ordre Traktor/Camelot wheel.
    
    Args:
        key1: Première clé musicale (ex: "Am", "C")
        key2: Seconde clé musicale (ex: "Em", "G")
        
    Returns:
        Distance entre les clés (0 = identiques, 1 = adjacentes, etc.)
        Retourne 999 si une des clés n'est pas reconnue
    """
    if not key1 or not key2:
        return 999
        
    # Normaliser les clés
    normalized_key1 = normalize_musical_key_notation(key1)
    normalized_key2 = normalize_musical_key_notation(key2)
    
    if not normalized_key1 or not normalized_key2:
        return 999
        
    # Obtenir les indices dans l'ordre Traktor
    index1 = TRAKTOR_KEY_INDEX.get(normalized_key1)
    index2 = TRAKTOR_KEY_INDEX.get(normalized_key2)
    
    if index1 is None or index2 is None:
        return 999
        
    # Calculer la distance absolue
    return abs(index1 - index2)


def get_traktor_key_order():
    """
    Retourne l'ordre des clés musicales selon Traktor (triées par couleur).
    
    Returns:
        Liste des clés dans l'ordre Traktor/Camelot wheel
    """
    return TRAKTOR_KEY_ORDER.copy()


def get_compatible_keys(base_key: str, max_distance: int = 1) -> list:
    """
    Retourne la liste des clés compatibles dans une distance donnée.
    
    Args:
        base_key: Clé de base (ex: "Am")
        max_distance: Distance maximale autorisée (défaut: 1)
        
    Returns:
        Liste des clés compatibles incluant la clé de base
    """
    if not base_key:
        return []
        
    normalized_base = normalize_musical_key_notation(base_key)
    if not normalized_base:
        return []
        
    base_index = TRAKTOR_KEY_INDEX.get(normalized_base)
    if base_index is None:
        return []
        
    N = len(TRAKTOR_KEY_ORDER)
    compatible_keys = []
    for key, index in TRAKTOR_KEY_INDEX.items():
        raw_dist = abs(index - base_index)
        distance = min(raw_dist, N - raw_dist)
        if distance <= max_distance:
            compatible_keys.append(key)
    return compatible_keys
