"""
Filtres de template pour les clés musicales et couleurs Traktor
"""

from django import template
from ..musical_key.utils import (
    get_traktor_color_from_musical_key,
    get_musical_key_info
)

register = template.Library()


@register.filter
def traktor_color(musical_key):
    """
    Filtre pour obtenir la couleur hexadécimale Traktor d'une clé musicale.
    
    Usage: {{ track.musical_key|traktor_color }}
    Returns: "#9370DB" pour "Dm", None si invalide
    """
    if not musical_key:
        return None
    
    color_info = get_traktor_color_from_musical_key(musical_key)
    return color_info['color_hex'] if color_info else None


@register.filter
def traktor_color_name(musical_key):
    """
    Filtre pour obtenir le nom de couleur Traktor d'une clé musicale.
    
    Usage: {{ track.musical_key|traktor_color_name }}
    Returns: "Violet" pour "Dm", None si invalide
    """
    if not musical_key:
        return None
    
    key_info = get_musical_key_info(musical_key)
    return key_info['color_name'] if key_info else None


@register.filter
def musical_key_info(musical_key):
    """
    Filtre pour obtenir toutes les infos d'une clé musicale.
    
    Usage: {{ track.musical_key|musical_key_info }}
    Returns: dict avec key, camelot, color_hex, etc.
    """
    if not musical_key:
        return {}
    return get_musical_key_info(musical_key)


@register.inclusion_tag('track/includes/musical_key_badge.html')
def musical_key_badge(musical_key, size='normal'):
    """
    Tag d'inclusion pour afficher une clé musicale avec sa couleur Traktor.
    
    Usage: {% musical_key_badge track.musical_key %}
           {% musical_key_badge track.musical_key "small" %}
    """
    if not musical_key:
        return {
            'musical_key': '--',
            'color_hex': '#cccccc',
            'color_name': 'Gris',
            'camelot': '',
            'size': size
        }
    
    info = get_musical_key_info(musical_key)
    
    # Si info est None, utiliser des valeurs par défaut
    if not info:
        return {
            'musical_key': musical_key,
            'color_hex': '#cccccc',
            'color_name': 'Inconnu',
            'camelot': '',
            'size': size
        }
    
    return {
        'musical_key': info.get('musical_key', musical_key),
        'color_hex': info.get('color_hex', '#cccccc'),
        'color_name': info.get('color_name', 'Inconnu'),
        'camelot': info.get('camelot', ''),
        'size': size
    }
