from django.http import JsonResponse
from ..models import Track
import json
import logging

logger = logging.getLogger(__name__)


def get_suggestions_for_track(track_id, bpm_range_percent=10, sort_by='playcount',
                            sort_order='desc', limit=50, genre_mode='exact',
                            ranking_min=1, musical_key_distance=12):
    """
    Fonction pour obtenir des suggestions avancées pour un track
    """
    try:
        track = Track.objects.get(id=track_id)
    except Track.DoesNotExist:
        return []

    # Construire la requête de base
    suggestions = Track.objects.exclude(id=track.id)

    # Filtrer par BPM si disponible
    if track.bpm:
        bpm_min = track.bpm * (1 - bpm_range_percent / 100)
        bpm_max = track.bpm * (1 + bpm_range_percent / 100)
        suggestions = suggestions.filter(bpm__gte=bpm_min, bpm__lte=bpm_max)

    # Filtrer par ranking minimum
    if ranking_min > 1:
        suggestions = suggestions.filter(ranking__gte=ranking_min)

    # Filtrer par genre selon le mode
    if track.genre and genre_mode == 'same':
        suggestions = suggestions.filter(genre=track.genre)
    elif track.genre and genre_mode == 'secondary':
        suggestions = suggestions.filter(comment__icontains=track.genre.name)

    # Filtrer par clé musicale (distance Camelot)
    if track.musical_key and musical_key_distance < 12:
        from track.musical_key.musical_key_utils import get_compatible_keys, normalize_musical_key_notation
        compatible_keys = get_compatible_keys(track.musical_key, musical_key_distance)
        # Nettoyer les clés compatibles
        compatible_keys_clean = [normalize_musical_key_notation(k) for k in compatible_keys if k]
        # Filtrer les suggestions avec nettoyage
        suggestions = suggestions.filter(musical_key__in=compatible_keys_clean)

    # Tri (désactivé, le tri se fait par Traktor order plus loin)
    # if sort_by == 'bpm':
    #     order_field = 'bpm' if sort_order == 'asc' else '-bpm'
    # elif sort_by == 'ranking':
    #     order_field = 'ranking' if sort_order == 'asc' else '-ranking'
    # elif sort_by == 'title':
    #     order_field = 'title' if sort_order == 'asc' else '-title'
    # elif sort_by == 'artist':
    #     order_field = 'artist__name' if sort_order == 'asc' else '-artist__name'
    # else:  # playcount par défaut
    #     order_field = 'playcount' if sort_order == 'asc' else '-playcount'

    # suggestions = suggestions.order_by(order_field)

    # Limiter les résultats (après tous les filtres)
    return list(suggestions)  # Limitation appliquée après tri dans la vue AJAX


def ajax_suggestions(request):
    """Vue AJAX pour obtenir des suggestions filtrées"""
    if request.method == 'POST':
        if request.content_type == 'application/json':
            params = json.loads(request.body)
            track_id = params.get('track_id')
            bpm_range = float(params.get('bpm_range', 10))
            sort_by = params.get('sort_by', 'playcount')
            sort_order = params.get('sort_order', 'desc')
            limit = int(params.get('limit', 50))
            genre_mode = params.get('genre_mode', 'same')
            ranking_min = int(params.get('ranking_min', 1))
            musical_key_distance = int(params.get('musical_key_distance', 12))
        else:
            track_id = request.POST.get('track_id')
            bpm_range = float(request.POST.get('bpm_range', 10))
            sort_by = request.POST.get('sort_by', 'playcount')
            sort_order = request.POST.get('sort_order', 'desc')
            limit = int(request.POST.get('limit', 50))
            genre_mode = request.POST.get('genre_mode', 'same')
            ranking_min = int(request.POST.get('ranking_min', 1))
            musical_key_distance = int(request.POST.get('musical_key_distance', 12))

        # Récupérer les suggestions avec les paramètres
        suggestions = get_suggestions_for_track(
            track_id,
            bpm_range_percent=bpm_range,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            genre_mode=genre_mode,
            ranking_min=ranking_min,
            musical_key_distance=musical_key_distance
        )
        # Calcul de la distance musicale via l'ordre Traktor
        current_order = None
        try:
            current_track = Track.objects.get(id=track_id)
            current_key_obj = current_track.get_musical_key_obj()
            if current_key_obj:
                current_order = current_key_obj.order
        except Track.DoesNotExist:
            current_order = None
        N = 24  # Nombre total de positions sur la Camelot wheel
        suggestions_data = []
        for track in suggestions:
            suggestion_key_obj = track.get_musical_key_obj()
            if current_order is not None and suggestion_key_obj:
                raw_dist = abs(suggestion_key_obj.order - current_order)
                key_distance = min(raw_dist, N - raw_dist)
            else:
                key_distance = None
            suggestions_data.append({
                'id': track.id,
                'title': track.title,
                'artist_name': track.artist.name,
                'genre_name': track.genre.name if track.genre else '',
                'bpm': track.bpm,
                'ranking': track.ranking,
                'playcount': track.playcount,
                'comment': track.comment,
                'musical_key': track.musical_key,
                'musical_key_color': track.get_musical_key_color(),
                'musical_key_distance': key_distance,
                'musical_key_order': suggestion_key_obj.order if suggestion_key_obj else None,
            })
        # Tri des suggestions par ordre Traktor (musical_key_order), puis limitation
        suggestions_data = sorted(suggestions_data, key=lambda x: x['musical_key_order'] if x['musical_key_order'] is not None else 999)
        suggestions_data = suggestions_data[:limit]
        return JsonResponse({
            'suggestions': suggestions_data,
            'count': len(suggestions_data)
        })
    return JsonResponse({'error': 'Method not allowed'}, status=405)
