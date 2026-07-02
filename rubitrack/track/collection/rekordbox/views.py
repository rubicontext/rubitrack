"""
Vues pour la synchronisation avec Rekordbox
"""

import io
import json
import os
import tempfile
import zipfile
from datetime import datetime
from typing import Any, Dict, List

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from track.models import Config

from .synchronize_rekordbox_collection import synchronize_rekordbox_collection


@staff_member_required
def rekordbox_sync_view(request):
    """
    Vue pour la page de synchronisation Rekordbox
    """
    return render(request, 'track/rekordbox/synchronize_rekordbox_collection.html')


@staff_member_required
@require_http_methods(["POST"])
def synchronize_rekordbox_collection_api(request):
    """
    API pour synchroniser les cue points avec un fichier Rekordbox.

    Succès: réponse ZIP (collection modifiée + liste des tracks non trouvées),
    stats résumées dans le header X-Sync-Stats (JSON).
    Erreur: réponse JSON avec le code HTTP approprié.
    """
    if 'rekordbox_file' not in request.FILES:
        return JsonResponse({
            'success': False,
            'error': 'Aucun fichier fourni'
        }, status=400)

    uploaded_file = request.FILES['rekordbox_file']

    # Validation du fichier
    if not uploaded_file.name.endswith('.xml'):
        return JsonResponse({
            'success': False,
            'error': 'Le fichier doit être un fichier XML'
        }, status=400)

    max_upload_size_mb = Config.get_config().max_upload_size_mb
    if uploaded_file.size > max_upload_size_mb * 1024 * 1024:
        return JsonResponse({
            'success': False,
            'error': f'Fichier trop volumineux ({uploaded_file.size // (1024 * 1024)} Mo, maximum {max_upload_size_mb} Mo)'
        }, status=413)

    # Création d'un fichier temporaire
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.xml', delete=False) as temp_file:
        for chunk in uploaded_file.chunks():
            temp_file.write(chunk)
        temp_file_path = temp_file.name

    # Fichier de sortie temporaire
    output_file_path = temp_file_path + '_output.xml'

    try:
        mode = request.POST.get('mode', 'overwrite')
        # Synchronisation des cue points
        stats = synchronize_rekordbox_collection(
            temp_file_path,
            output_file_path,
            mode=mode
        )

        if not stats['success']:
            # Fichier illisible ou pas un export Rekordbox: erreur côté client
            return JsonResponse(
                {'success': False, 'error': stats.get('error', 'Erreur inconnue')},
                status=400,
            )

        current_date = datetime.now().strftime('%Y%m%d')
        xml_filename = f'rekordbox_collection_with_cues_{current_date}.xml'
        not_found_filename = f'rekordbox_tracks_not_found_{current_date}.txt'
        not_found_content = generate_not_found_file(stats['unmatched_rekordbox_tracks'])

        # Construction du ZIP en mémoire (XML modifié + tracks non trouvées)
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(output_file_path, arcname=xml_filename)
            zf.writestr(not_found_filename, not_found_content)

        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = (
            f'attachment; filename="rekordbox_sync_{current_date}.zip"'
        )
        response['X-Sync-Stats'] = json.dumps({
            'mode': mode,
            'total_tracks_in_rekordbox_file': stats['total_tracks_in_rekordbox_file'],
            'rubitrack_tracks_processed': stats['rubitrack_tracks_processed'],
            'tracks_found_and_matched': stats['tracks_found_and_matched'],
            'tracks_updated_with_cue_points': stats['tracks_updated_with_cue_points'],
            'total_cue_points_added': stats['total_cue_points_added'],
            'unmatched_count': len(stats['unmatched_rekordbox_tracks']),
        })
        return response

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erreur lors de la synchronisation: {str(e)}'
        }, status=500)

    finally:
        # Nettoyage des fichiers temporaires
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        if os.path.exists(output_file_path):
            os.unlink(output_file_path)


def generate_not_found_file(unmatched_tracks: List[Dict[str, Any]]) -> str:
    """Génère le contenu du fichier des tracks non trouvées"""
    lines: List[str] = []
    for t in unmatched_tracks:
        title = t.get('title') or t.get('Name') or ''
        artist = t.get('artist') or t.get('Artist') or ''
        lines.append(f"{artist} - {title}")
    return "\n".join(lines)


@staff_member_required
@require_http_methods(["GET"])
def cue_points_stats_api(request) -> JsonResponse:
    """
    API pour obtenir les statistiques des cue points
    """
    try:
        from track.models import Track, TrackCuePoints

        total_tracks = Track.objects.count()
        tracks_with_cue_points = Track.objects.filter(cue_points__isnull=False).count()

        # Compte des cue points par position
        cue_points_count = {}
        for i in range(1, 9):
            count = TrackCuePoints.objects.exclude(**{f'cue_point_{i}__isnull': True}).count()
            cue_points_count[f'cue_point_{i}'] = count

        return JsonResponse({
            'success': True,
            'stats': {
                'total_tracks': total_tracks,
                'tracks_with_cue_points': tracks_with_cue_points,
                'tracks_without_cue_points': total_tracks - tracks_with_cue_points,
                'cue_points_by_position': cue_points_count
            }
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erreur lors du calcul des statistiques: {str(e)}'
        }, status=500)
