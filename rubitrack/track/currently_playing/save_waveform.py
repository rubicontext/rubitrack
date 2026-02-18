"""
Vue pour sauvegarder une image de waveform depuis le presse-papier
"""
import base64
import os
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from ..models import Track
import json


@require_POST
def save_waveform(request):
    """
    Sauvegarde une image de waveform pour une track
    
    Args:
        request: HttpRequest avec track_id et image_data (base64) en JSON
        
    Returns:
        JsonResponse avec success/error
    """
    try:
        # Parser le JSON body
        data = json.loads(request.body)
        track_id = data.get('track_id')
        image_data = data.get('image_data')
        
        if not track_id or not image_data:
            return JsonResponse({'success': False, 'error': 'Missing track_id or image_data'})
        
        # Récupérer la track
        try:
            track = Track.objects.get(id=track_id)
        except Track.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Track not found'})
        
        # Extraire les données base64 (enlever le préfixe data:image/png;base64,)
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        # Décoder le base64
        image_bytes = base64.b64decode(image_data)
        
        # Créer le dossier pour les waveforms si nécessaire
        waveforms_dir = os.path.join(settings.MEDIA_ROOT, 'waveforms')
        os.makedirs(waveforms_dir, exist_ok=True)
        
        # Nom de fichier basé sur l'ID de la track
        filename = f'waveform_track_{track_id}.png'
        filepath = os.path.join(waveforms_dir, filename)
        
        # Sauvegarder l'image
        with open(filepath, 'wb') as f:
            f.write(image_bytes)
        
        # Sauvegarder le chemin relatif dans la track (si le modèle a un champ pour ça)
        # Pour l'instant on retourne juste success
        relative_path = os.path.join('waveforms', filename)
        
        # Si le modèle Track a un champ waveform_image, le mettre à jour
        # track.waveform_image = relative_path
        # track.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Waveform saved successfully',
            'path': relative_path
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
