"""Template filters & tags for musical keys and Traktor colors"""
from django import template
from ..musical_key.musical_key_utils import (
    get_traktor_color_from_musical_key,
    get_musical_key_info
)

register = template.Library()

@register.filter
def traktor_color(musical_key):
    if not musical_key:
        return None
    color_info = get_traktor_color_from_musical_key(musical_key)
    return color_info['color_hex'] if color_info else None

@register.filter
def traktor_color_name(musical_key):
    if not musical_key:
        return None
    key_info = get_musical_key_info(musical_key)
    return key_info['color_name'] if key_info else None

@register.filter
def musical_key_info(musical_key):
    if not musical_key:
        return {}
    return get_musical_key_info(musical_key)

@register.inclusion_tag('track/includes/musical_key_badge.html')
def musical_key_badge(musical_key, size='normal'):
    if not musical_key:
        return {
            'musical_key': '--',
            'color_hex': '#cccccc',
            'color_name': 'Gris',
            'camelot': '',
            'size': size
        }
    info = get_musical_key_info(musical_key)
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
