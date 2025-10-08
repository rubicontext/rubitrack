from django.urls import path

from . import views
from .collection import import_collection
from .currently_playing.currently_playing import (
    display_currently_playing,
    display_history_editing,
    get_more_played_history_row,
    get_more_playlist_history_table,
    get_more_currently_playing_title_block,
    get_more_currently_playing_track_block,
    get_more_suggestion_auto_block,
    get_more_transition_block,
    get_more_transition_block_history,
    get_all_currently_playing_data,
    ajax_cue_points
)
from .currently_playing.transition_view import (
    add_new_transition,
    delete_transition,
    update_transition_comment
)
from .playlist import playlist_transitions
from .duplicate.display_duplicate import display_duplicates, manual_merge_track_batch, merge_tracks, bulk_merge_tracks
from .currently_playing.manual_transition import manual_transition
from .duplicate.manual_merge_duplicate import manual_merge_duplicate
from .duplicate.manual_merge_artist import manual_merge_artist
from .currently_playing.suggestions_block_view import ajax_suggestions, suggestions_block
from .config_views import config_view, config_reset_view
from .tools_views import tools_index, cleanup_musical_keys, cue_points_overview
from .views_import_musical_keys import import_musical_keys_view

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
    path('currently_playing/', display_currently_playing, name='currently_playing_view'),
    path('history_editing/<int:track_id>', display_history_editing, name='history_editing_view'),
    # TRANSITIONS
    path('add_new_transition/', add_new_transition, name='add_new_transition_view'),
    path('delete_transition/', delete_transition, name='delete_transition_view'),
    path(
        'update_transition_comment/', update_transition_comment, name='update_transition_comment_view'
    ),
    path(
        'get_more_played_history_row/',
        get_more_played_history_row,
        name='get_more_played_history_row',
    ),
    path(
        'get_more_playlist_history_table/',
        get_more_playlist_history_table,
        name='get_more_playlist_history_table',
    ),
    path(
        'get_more_currently_playing_title_block/',
        get_more_currently_playing_title_block,
        name='get_more_currently_playing_title_block',
    ),
    path(
        'get_more_currently_playing_track_block/',
        get_more_currently_playing_track_block,
        name='get_more_currently_playing_track_block',
    ),
    path(
        'get_more_suggestion_auto_block/',
        get_more_suggestion_auto_block,
        name='get_more_suggestion_auto_block',
    ),
    path('get_more_transition_block/', get_more_transition_block, name='get_more_transition_block'),
    path(
        'get_more_transition_block_history/',
        get_more_transition_block_history,
        name='get_more_transition_block_history',
    ),
    path(
        'get_all_currently_playing_data/',
        get_all_currently_playing_data,
        name='get_all_currently_playing_data',
    ),
    path('ajax_cue_points/', ajax_cue_points, name='ajax_cue_points'),
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
    path('tools/', tools_index, name='tools'),
    path('duplicates/', display_duplicates, name='duplicates'),
    path('manual_merge_track_batch/', manual_merge_track_batch, name='manual_merge_track_batch'),
    path('merge_tracks/', merge_tracks, name='merge_tracks'),
    path('bulk_merge_tracks/', bulk_merge_tracks, name='bulk_merge_tracks'),
    path('manual_transition/', manual_transition, name='manual_transition'),
    path('manual_merge_track/', manual_merge_duplicate, name='manual_merge_track'),
    path('manual_merge_artist/', manual_merge_artist, name='manual_merge_artist'),
    # SUGGESTIONS
    path('ajax_suggestions/', ajax_suggestions, name='ajax_suggestions'),
    path('suggestions_block/<int:track_id>/', suggestions_block, name='suggestions_block'),
    path('test_suggestions/<int:track_id>/', suggestions_block, name='test_suggestions'),
    # CONFIGURATION
    path('config/', config_view, name='config'),
    path('config/reset/', config_reset_view, name='config_reset'),
    # TOOLS
    path('tools/', tools_index, name='tools'),
    path('tools/cleanup_musical_keys/', cleanup_musical_keys, name='cleanup_musical_keys'),
    path('tools/cue_points/', cue_points_overview, name='cue_points_overview'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

urlpatterns += [
    path('admin/import-musical-keys/', import_musical_keys_view, name='import_musical_keys'),
]
