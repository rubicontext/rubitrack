from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from ..models import Track, Artist, Genre, Config
from ..currently_playing.suggestions import get_list_track_suggestions_auto
import json


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
        from rubitrack.track.musical_key.musical_key_utils import get_compatible_keys, normalize_musical_key_notation
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


def get_compatible_keys(key, max_distance):
    """
    Retourne les clés musicales compatibles selon la roue Camelot
    """
    if not key:
        return []
    
    # Mapping simplifié des clés Camelot (à étendre selon vos besoins)
    camelot_wheel = {
        '1A': ['1A', '1B', '2A', '12A'],
        '1B': ['1A', '1B', '2B', '12B'],
        '2A': ['1A', '2A', '2B', '3A'],
        '2B': ['1B', '2B', '2A', '3B'],
        # ... etc pour toutes les clés
    }
    
    if max_distance >= 12:
        return None  # Pas de filtre
    
    compatible = camelot_wheel.get(key, [key])
    
    # Ajouter plus de clés selon la distance
    if max_distance > 1:
        # Logique pour étendre les clés compatibles
        pass
    
    return compatible


def suggestions_view(request, track_id):
    """Vue pour afficher les suggestions d'un track"""
    try:
        current_track = Track.objects.get(id=track_id)
    except Track.DoesNotExist:
        current_track = None
    
    # Récupérer les paramètres de configuration
    config = Config.get_config()
    default_bpm_range = config.default_bpm_range_suggestions
    default_musical_key_distance = config.default_musical_key_distance
    default_ranking_min = config.default_ranking_min
    
    # Suggestions initiales (tri par playcount décroissant par défaut)
    initial_suggestions = get_suggestions_for_track(
        track_id, 
        bpm_range_percent=default_bpm_range,
        sort_by='playcount',
        sort_order='desc',
        ranking_min=default_ranking_min,
        musical_key_distance=default_musical_key_distance
    ) if current_track else []
    
    context = {
        'current_track': current_track,
        'suggestions': initial_suggestions,
        'bpm_range': default_bpm_range,
        'default_musical_key_distance': default_musical_key_distance,
        'default_ranking_min': default_ranking_min,
        'genre_mode': 'exact'  # Valeur par défaut
    }
    
    return render(request, 'track/suggestions.html', context)


@csrf_exempt
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
        # Récupérer la clé musicale du track courant une seule fois
        try:
            current_track = Track.objects.get(id=track_id)
            current_musical_key = current_track.musical_key
        except Track.DoesNotExist:
            current_musical_key = None
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
        # DEBUG : log des clés compatibles et suggestions avant filtrage
        if current_track and current_track.musical_key and musical_key_distance < 12:
            from rubitrack.track.musical_key.musical_key_utils import get_compatible_keys
            compatible_keys = get_compatible_keys(current_track.musical_key, musical_key_distance)
            print(f"Clés compatibles pour {current_track.musical_key} (distance {musical_key_distance}) : {compatible_keys}")
            print(f"Suggestions avant filtrage : {[t.musical_key for t in Track.objects.exclude(id=current_track.id)]}")
        print(f"AJAX params: track_id={track_id}, bpm_range={bpm_range}, ranking_min={ranking_min}, musical_key_distance={musical_key_distance}, genre_mode={genre_mode}")
        print(f"Suggestions trouvées: {len(suggestions)}")
        
        # Tri des suggestions par ordre Traktor (musical_key_order), puis limitation
        suggestions_data = sorted(suggestions_data, key=lambda x: x['musical_key_order'] if x['musical_key_order'] is not None else 999)
        suggestions_data = suggestions_data[:limit]
        return JsonResponse({
            'suggestions': suggestions_data,
            'count': len(suggestions_data)
        })
    return JsonResponse({'error': 'Method not allowed'}, status=405)


def get_artists_suggestions(request):
    """Vue pour obtenir des suggestions d'artistes (pour l'autocomplétion)"""
    query = request.GET.get('q', '')
    if len(query) >= 2:
        artists = Artist.objects.filter(
            name__icontains=query
        ).order_by('name')[:10]
        
        artists_data = []
        for artist in artists:
            artists_data.append({
                'id': artist.id,
                'name': artist.name
            })
        
        return JsonResponse({'artists': artists_data})
    
    return JsonResponse({'artists': []})


def get_genres_suggestions(request):
    """Vue pour obtenir des suggestions de genres (pour l'autocomplétion)"""
    query = request.GET.get('q', '')
    if len(query) >= 1:
        genres = Genre.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        ).order_by('name')[:10]
        
        genres_data = []
        for genre in genres:
            genres_data.append({
                'id': genre.id,
                'name': genre.name,
                'description': genre.description
            })
        
        return JsonResponse({'genres': genres_data})
    
    return JsonResponse({'genres': []})


def advanced_search(request):
    """Vue pour la recherche avancée de tracks"""
    if request.method == 'POST':
        # Paramètres de recherche
        artist_query = request.POST.get('artist', '').strip()
        title_query = request.POST.get('title', '').strip()
        genre_query = request.POST.get('genre', '').strip()
        bpm_min = request.POST.get('bpm_min', '')
        bpm_max = request.POST.get('bpm_max', '')
        ranking_min = request.POST.get('ranking_min', '')
        ranking_max = request.POST.get('ranking_max', '')
        musical_key = request.POST.get('musical_key', '').strip()
        
        # Construction de la requête
        tracks = Track.objects.all()
        
        if artist_query:
            tracks = tracks.filter(artist__name__icontains=artist_query)
        
        if title_query:
            tracks = tracks.filter(title__icontains=title_query)
        
        if genre_query:
            tracks = tracks.filter(genre__name__icontains=genre_query)
        
        if bpm_min:
            tracks = tracks.filter(bpm__gte=float(bpm_min))
        
        if bpm_max:
            tracks = tracks.filter(bpm__lte=float(bpm_max))
        
        if ranking_min:
            tracks = tracks.filter(ranking__gte=int(ranking_min))
        
        if ranking_max:
            tracks = tracks.filter(ranking__lte=int(ranking_max))
        
        if musical_key:
            tracks = tracks.filter(musical_key__iexact=musical_key)
        
        # Limiter le nombre de résultats
        tracks = tracks.order_by('-playcount')[:100]
        
        # Formater les données
        tracks_data = []
        for track in tracks:
            tracks_data.append({
                'id': track.id,
                'title': track.title,
                'artist': track.artist.name,
                'bpm': track.bpm,
                'ranking': track.ranking,
                'playcount': track.playcount,
                'genre': track.genre.name if track.genre else '',
                'musical_key': track.musical_key,
                'musical_key_color': track.get_musical_key_color()
            })
        
        return JsonResponse({
            'tracks': tracks_data,
            'count': len(tracks_data)
        })
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


def get_track_details(request, track_id):
    """Vue pour obtenir les détails d'un track"""
    try:
        track = Track.objects.get(id=track_id)
        
        track_data = {
            'id': track.id,
            'title': track.title,
            'artist': track.artist.name,
            'genre': track.genre.name if track.genre else '',
            'bpm': track.bpm,
            'ranking': track.ranking,
            'playcount': track.playcount,
            'musical_key': track.musical_key,
            'musical_key_color': track.get_musical_key_color(),
            'path': track.path,
            'year': track.year,
            'comment': track.comment,
            'size': track.size,
            'seconds': track.seconds,
            'last_played': track.last_played.isoformat() if track.last_played else None,
            'date_added': track.date_added.isoformat() if track.date_added else None
        }
        
        return JsonResponse({'track': track_data})
        
    except Track.DoesNotExist:
        return JsonResponse({'error': 'Track not found'}, status=404)


def get_musical_key_suggestions(request):
    """Vue pour obtenir des suggestions de clés musicales"""
    query = request.GET.get('q', '').strip().upper()
    
    # Liste des clés musicales possibles (notation Camelot)
    camelot_keys = [
        '1A', '1B', '2A', '2B', '3A', '3B', '4A', '4B', '5A', '5B', '6A', '6B',
        '7A', '7B', '8A', '8B', '9A', '9B', '10A', '10B', '11A', '11B', '12A', '12B'
    ]
    
    if query:
        filtered_keys = [key for key in camelot_keys if key.startswith(query)]
    else:
        filtered_keys = camelot_keys
    
    keys_data = []
    for key in filtered_keys[:12]:  # Limiter à 12 résultats
        keys_data.append({
            'value': key,
            'label': key
        })
    
    return JsonResponse({'keys': keys_data})
