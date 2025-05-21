from django.urls import path

from . import views
from . import import_collection
from . import currently_playing
from . import transition_view
from .playlist import playlist_transitions

from django.views.generic.base import RedirectView
from django.contrib.staticfiles.storage import staticfiles_storage
from django.views.generic.base import RedirectView
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('', views.index, name='index'),
    path('favicon.ico', RedirectView.as_view(url=staticfiles_storage.url('favicon.ico'))),
    path('static/favicon.ico', RedirectView.as_view(url=staticfiles_storage.url('favicon.ico'))),
    path('import_collection/', import_collection.upload_file, name='import_collection_view'),
    path('currently_playing/', currently_playing.display_currently_playing, name='currently_playing_view'),
    path('history_editing/<int:trackId>', currently_playing.display_history_editing, name='history_editing_view'),
    # TRANSITIONS
    path('add_new_transition/', transition_view.add_new_transition, name='add_new_transition_view'),
    path('delete_transition/', transition_view.delete_transition, name='delete_transition_view'),
    path(
        'update_transition_comment/', transition_view.update_transition_comment, name='update_transition_comment_view'
    ),
    path(
        'get_more_played_history_row/',
        currently_playing.get_more_played_history_row,
        name='get_more_played_history_row',
    ),
    path(
        'get_more_playlist_history_table/',
        currently_playing.get_more_playlist_history_table,
        name='get_more_playlist_history_table',
    ),
    path(
        'get_more_currently_playing_title_block/',
        currently_playing.get_more_currently_playing_title_block,
        name='get_more_currently_playing_title_block',
    ),
    path(
        'get_more_currently_playing_track_block/',
        currently_playing.get_more_currently_playing_track_block,
        name='get_more_currently_playing_track_block',
    ),
    path(
        'get_more_suggestion_auto_block/',
        currently_playing.get_more_suggestion_auto_block,
        name='get_more_suggestion_auto_block',
    ),
    path('get_more_transition_block/', currently_playing.get_more_transition_block, name='get_more_transition_block'),
    path(
        'get_more_transition_block_history/',
        currently_playing.get_more_transition_block_history,
        name='get_more_transition_block_history',
    ),
    # PLAYLISTS
    path(
        'playlist_transitions/<int:PlaylistId>',
        playlist_transitions.display_playlist_transitions,
        name='playlist_transitions_view',
    ),
    path(
        'delete_playlist_transitions/',
        playlist_transitions.delete_playlist_transitions,
        name='delete_playlist_transition_view',
    ),
    path(
        'delete_all_generated_transitions/',
        playlist_transitions.delete_all_generated_transitions,
        name='delete_all_generated_transitions_view',
    ),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
