# Peuple la table MusicalKey (données de référence pour le tri par clé musicale).
# Elle n'était alimentée que manuellement via la vue admin -> vide sur toute base
# fraîche (dont la prod PG16), ce qui cassait le tri des suggestions par clé.

from django.db import migrations


def populate_musical_keys(apps, schema_editor):
    MusicalKey = apps.get_model('track', 'MusicalKey')
    from track.musical_key.musical_key_utils import (
        CAMELOT_TO_MUSICAL, OPEN_KEY_TO_MUSICAL, CAMELOT_COLORS, TRAKTOR_KEY_ORDER,
    )
    musical_to_camelot = {v: k for k, v in CAMELOT_TO_MUSICAL.items()}
    musical_to_open = {v: k for k, v in OPEN_KEY_TO_MUSICAL.items()}
    for order, musical in enumerate(TRAKTOR_KEY_ORDER, start=1):
        camelot = musical_to_camelot.get(musical)
        open_key = musical_to_open.get(musical)
        color_info = CAMELOT_COLORS.get(camelot, {}) if camelot else {}
        color = color_info.get('color_hex', '') or color_info.get('color_name', '')
        MusicalKey.objects.update_or_create(
            musical=musical,
            defaults={
                'camelot': camelot or '',
                'open': open_key or '',
                'traktor_color': color,
                'order': order,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ('track', '0029_mergelog_duplicatecandidate'),
    ]

    operations = [
        migrations.RunPython(populate_musical_keys, migrations.RunPython.noop),
    ]
