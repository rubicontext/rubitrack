from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect
from track.models_musicalkey import MusicalKey
from track.musical_key_utils import CAMELOT_TO_MUSICAL, OPEN_KEY_TO_MUSICAL, CAMELOT_COLORS, TRAKTOR_KEY_ORDER

def import_musical_keys():
    musical_to_camelot = {v: k for k, v in CAMELOT_TO_MUSICAL.items()}
    musical_to_open = {v: k for k, v in OPEN_KEY_TO_MUSICAL.items()}
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

@staff_member_required
def import_musical_keys_view(request):
    if request.method == 'POST':
        import_musical_keys()
        return render(request, 'admin/import_musical_keys_done.html')
    return render(request, 'admin/import_musical_keys.html')
