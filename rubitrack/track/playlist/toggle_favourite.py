from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from ..models import Config


@login_required
@require_POST
def toggle_playlist_favourite(request):
    """
    Toggle a playlist ID in the favourite playlists list
    Expects POST data: playlist_id
    Returns: {'success': True, 'is_favourite': True/False, 'favourites': '1;2;3'}
    """
    try:
        playlist_id = request.POST.get('playlist_id')
        if not playlist_id:
            return JsonResponse({'success': False, 'error': 'Missing playlist_id'}, status=400)
        
        playlist_id = str(playlist_id).strip()
        
        config = Config.get_config()
        current_favourites = config.default_playlist_favourites or ''
        
        # Parse current favourites
        favourite_ids = [x.strip() for x in current_favourites.split(';') if x.strip()]
        
        # Toggle the playlist_id
        if playlist_id in favourite_ids:
            favourite_ids.remove(playlist_id)
            is_favourite = False
        else:
            favourite_ids.append(playlist_id)
            is_favourite = True
        
        # Save back to config
        new_favourites = ';'.join(favourite_ids)
        config.default_playlist_favourites = new_favourites
        config.save()
        
        return JsonResponse({
            'success': True,
            'is_favourite': is_favourite,
            'favourites': new_favourites
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
