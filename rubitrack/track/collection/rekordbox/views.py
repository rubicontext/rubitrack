"""
Vues pour la synchronisation avec Rekordbox
"""

from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.admin.views.decorators import staff_member_required
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from datetime import datetime
import tempfile
import os

from .synchronize_rekordbox_collection import synchronize_rekordbox_collection


@staff_member_required
def rekordbox_sync_view(request):
    """
    Vue pour la page de synchronisation Rekordbox
    """
    return render(request, 'track/rekordbox/synchronize_rekordbox_collection.html')


@staff_member_required
@csrf_exempt
@require_http_methods(["POST"])
def synchronize_rekordbox_collection_api(request):
    """
    API pour synchroniser les cue points avec un fichier Rekordbox
    """
    try:
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
                overwrite_existing=(mode == 'overwrite'),
                mode=mode
            )
            
            if stats['success']:
                # Génération du nom de fichier avec la date
                current_date = datetime.now().strftime('%Y%m%d')
                filename = f'rekordbox_collection_with_cues_{current_date}.xml'
                
                # Génération du fichier des tracks non trouvées
                not_found_content = generate_not_found_file(stats['unmatched_rekordbox_tracks'])
                not_found_filename = f'rekordbox_tracks_not_found_{current_date}.txt'
                
                # Lecture du fichier modifié pour le téléchargement
                with open(output_file_path, 'rb') as f:
                    xml_content = f.read()
                
                # Retour des deux fichiers via JSON
                response_data = {
                    'success': True,
                    'xml_file': {
                        'content': xml_content.decode('utf-8'),
                        'filename': filename,
                        'type': 'application/xml'
                    },
                    'not_found_file': {
                        'content': not_found_content,
                        'filename': not_found_filename,
                        'type': 'text/plain'
                    },
                    'stats': {
                        'total_tracks_in_rekordbox_file': stats['total_tracks_in_rekordbox_file'],
                        'rubitrack_tracks_processed': stats['rubitrack_tracks_processed'],
                        'tracks_found_and_matched': stats['tracks_found_and_matched'],
                        'tracks_updated_with_cue_points': stats['tracks_updated_with_cue_points'],
                        'total_cue_points_added': stats['total_cue_points_added'],
                        'unmatched_count': len(stats['unmatched_rekordbox_tracks'])
                    },
                    'mode': mode
                }
                
                return JsonResponse(response_data)
            else:
                return JsonResponse(stats, status=500)
        
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
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erreur interne: {str(e)}'
        }, status=500)


def generate_not_found_file(unmatched_tracks: list[dict]) -> str:
    """Génère le contenu du fichier des tracks non trouvées"""
    if not unmatched_tracks:
        return "Aucune track Rekordbox non trouvée dans la collection Rubitrack.\n"
    
    content = f"Tracks Rekordbox non trouvées dans la collection Rubitrack ({len(unmatched_tracks)})\n"
    content += "=" * 70 + "\n\n"
    
    for track in unmatched_tracks:
        title = track.get('title', 'Sans titre')
        artist = track.get('artist', 'Artiste inconnu')
        content += f"• {title} - {artist}\n"
    
    content += f"\nGénéré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}\n"
    return content


@staff_member_required
@require_http_methods(["GET"])
def cue_points_stats_api(request) -> JsonResponse:  # type: ignore[override]
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
