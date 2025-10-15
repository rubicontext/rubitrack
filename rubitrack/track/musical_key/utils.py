"""Musical key utilities (moved from musical_key_utils.py)"""
# ...existing code...

import re
from typing import Optional, Tuple

# Correspondance Camelot Wheel vers notation musicale traditionnelle
CAMELOT_TO_MUSICAL = {
    '1B': 'B', '2B': 'F#', '3B': 'Db', '4B': 'Ab', '5B': 'Eb', '6B': 'Bb',
    '7B': 'F', '8B': 'C', '9B': 'G', '10B': 'D', '11B': 'A', '12B': 'E',
    '1A': 'Abm', '2A': 'Ebm', '3A': 'Bbm', '4A': 'Fm', '5A': 'Cm', '6A': 'Gm',
    '7A': 'Dm', '8A': 'Am', '9A': 'Em', '10A': 'Bm', '11A': 'F#m', '12A': 'C#m'
}
OPEN_KEY_TO_MUSICAL = {
    '1d': 'B', '2d': 'F#', '3d': 'Db', '4d': 'Ab', '5d': 'Eb', '6d': 'Bb',
    '7d': 'F', '8d': 'C', '9d': 'G', '10d': 'D', '11d': 'A', '12d': 'E',
    '1m': 'Abm', '2m': 'Ebm', '3m': 'Bbm', '4m': 'Fm', '5m': 'Cm', '6m': 'Gm',
    '7m': 'Dm', '8m': 'Am', '9m': 'Em', '10m': 'Bm', '11m': 'F#m', '12m': 'C#m'
}
MUSICAL_TO_CAMELOT = {v: k for k, v in CAMELOT_TO_MUSICAL.items()}
MUSICAL_TO_OPEN_KEY = {v: k for k, v in OPEN_KEY_TO_MUSICAL.items()}

# ...existing code...

def normalize_musical_key_notation(key_string: str) -> Optional[str]:
    if not key_string:
        return None
    key_string = key_string.strip()
    if is_traditional_musical_notation(key_string):
        return standardize_traditional_notation(key_string)
    camelot_match = re.search(r'\b(\d{1,2}[AB])\b', key_string, re.IGNORECASE)
    if camelot_match:
        return CAMELOT_TO_MUSICAL.get(camelot_match.group(1).upper())
    open_key_match = re.search(r'\b(\d{1,2}[md])\b', key_string, re.IGNORECASE)
    if open_key_match:
        return OPEN_KEY_TO_MUSICAL.get(open_key_match.group(1).lower())
    return None

def is_traditional_musical_notation(key_string: str) -> bool:
    return bool(re.match(r'^[A-G][#b]?m?$', key_string.strip(), re.IGNORECASE))

def standardize_traditional_notation(key_string: str) -> str:
    key_string = key_string.strip()
    if not key_string:
        return key_string
    result = key_string[0].upper()
    if len(key_string) > 1:
        rest = re.sub(r'M$', 'm', key_string[1:], flags=re.IGNORECASE)
        result += rest
    return result

def extract_musical_key_from_filename(filename: str) -> Optional[str]:
    if not filename:
        return None
    patterns = [r'\b([1-9]|1[0-2])[AB]\b', r'\b([1-9]|1[0-2])[md]\b', r'\b([A-G][#♯b♭]?m?)\b', r'[-_\s]([A-G][#♯b♭]?m?)[- _\s]', r'[-_]([A-G][#♯b♭]?m?)(?=\.[a-zA-Z0-9]+$)']
    for pattern in patterns:
        matches = re.finditer(pattern, filename, re.IGNORECASE)
        for match in matches:
            key_candidate = match.group(1)
            normalized = normalize_musical_key_notation(key_candidate)
            if normalized:
                return normalized
    return None

def extract_musical_key_from_title(title: str) -> Optional[str]:
    return extract_musical_key_from_filename(title) if title else None

def get_conflicting_musical_keys(filename: str, db_musical_key: str) -> Tuple[Optional[str], Optional[str], bool]:
    filename_key = extract_musical_key_from_filename(filename)
    db_key = normalize_musical_key_notation(db_musical_key) if db_musical_key else None
    has_conflict = filename_key is not None and db_key is not None and filename_key != db_key
    return filename_key, db_key, has_conflict

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

def get_traktor_color_from_musical_key(musical_key: str):
    if not musical_key:
        return None
    normalized_key = normalize_musical_key_notation(musical_key)
    if not normalized_key:
        return None
    camelot_key = MUSICAL_TO_CAMELOT.get(normalized_key)
    if not camelot_key:
        return None
    return CAMELOT_COLORS.get(camelot_key)

def get_musical_key_info(musical_key: str):
    if not musical_key:
        return None
    normalized_key = normalize_musical_key_notation(musical_key)
    if not normalized_key:
        return None
    camelot_key = MUSICAL_TO_CAMELOT.get(normalized_key)
    if not camelot_key:
        return None
    color_info = CAMELOT_COLORS.get(camelot_key, {})
    return {
        'musical_key': normalized_key,
        'camelot': camelot_key,
        'color_hex': color_info.get('color_hex'),
        'color_name': color_info.get('color_name')
    }
TRAKTOR_KEY_ORDER = ['Am', 'Em', 'Bm', 'F#m', 'C#m', 'Abm', 'Ebm', 'Bbm', 'Fm', 'Cm', 'Gm', 'Dm', 'C', 'G', 'D', 'A', 'E', 'B', 'F#', 'Db', 'Ab', 'Eb', 'Bb', 'F']
TRAKTOR_KEY_INDEX = {key: index for index, key in enumerate(TRAKTOR_KEY_ORDER)}

def get_musical_key_distance(key1: str, key2: str) -> int:
    if not key1 or not key2:
        return 999
    normalized_key1 = normalize_musical_key_notation(key1)
    normalized_key2 = normalize_musical_key_notation(key2)
    if not normalized_key1 or not normalized_key2:
        return 999
    index1 = TRAKTOR_KEY_INDEX.get(normalized_key1)
    index2 = TRAKTOR_KEY_INDEX.get(normalized_key2)
    if index1 is None or index2 is None:
        return 999
    return abs(index1 - index2)

def get_traktor_key_order():
    return TRAKTOR_KEY_ORDER.copy()

def get_compatible_keys(base_key: str, max_distance: int = 1) -> list:
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
