from rubitrack.track.musical_key.models_musicalkey import MusicalKey
from rubitrack.track.musical_key.musical_key_utils import CAMELOT_TO_MUSICAL, OPEN_KEY_TO_MUSICAL, CAMELOT_COLORS, TRAKTOR_KEY_ORDER

# Construction du mapping musical -> camelot/open
musical_to_camelot = {v: k for k, v in CAMELOT_TO_MUSICAL.items()}
musical_to_open = {v: k for k, v in OPEN_KEY_TO_MUSICAL.items()}

# Remplir la table MusicalKey
for order, musical in enumerate(TRAKTOR_KEY_ORDER, start=1):
    camelot = musical_to_camelot.get(musical)
    open_key = musical_to_open.get(musical)
    color_info = CAMELOT_COLORS.get(camelot, {}) if camelot else {}
    color_hex = color_info.get('color_hex', '')
    color_name = color_info.get('color_name', '')
    MusicalKey.objects.update_or_create(
        musical=musical,
        defaults={
            'camelot': camelot or '',
            'open': open_key or '',
            'traktor_color': color_hex or color_name,
            'order': order
        }
    )
print("Import des clés musicales terminé.")
