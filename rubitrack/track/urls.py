from django.urls import path

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
from .playlist import playlist_transitions, playlist_favourite
from .playlist.toggle_favourite import toggle_playlist_favourite
from .playlist.playlist_list_view import playlist_list_view
from .navigation_view import navigation_view
from .duplicate.display_duplicate import (
    auto_merge_certain,
    dismiss_candidate,
    display_duplicates,
    manual_merge_track_batch,
    merge_artist_groups,
    merge_candidate,
    scan_duplicates_view,
)
from .currently_playing.manual_transition import manual_transition
from .currently_playing.save_waveform import save_waveform
from .duplicate.manual_merge_duplicate import manual_merge_duplicate
from .duplicate.manual_merge_artist import manual_merge_artist
from .suggestions.suggestions_view import ajax_suggestions
from .config.config_views import config_view, config_reset_view
from .config.tools_views import (
    cleanup_musical_keys,
    cue_points_overview,
    delete_all_cue_points,
    tools_index,
)
from .set_transitions.views import set_transitions_view, add_set_transition
from .currently_playing.set_history import display_sets
from .set_builder.set_builder_view import set_builder_view, set_builder_graph_api
from .ui_lab.ui_lab_view import ui_lab_view
from .pwa.views import manifest_view, service_worker_view
from .musical_key.views_import_musical_keys import import_musical_keys_view
from .collection.rekordbox.views import (
    rekordbox_sync_view,
    synchronize_rekordbox_collection_api,
    cue_points_stats_api
)

from django.views.generic.base import RedirectView
from django.contrib.staticfiles.storage import staticfiles_storage
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('favicon.ico', RedirectView.as_view(url=staticfiles_storage.url('favicon.ico'))),
    path('static/favicon.ico', RedirectView.as_view(url=staticfiles_storage.url('favicon.ico'))),
    path('', navigation_view, name='navigation'),
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
    path('duplicates/', display_duplicates, name='duplicates'),
    path('manual_merge_track_batch/', manual_merge_track_batch, name='manual_merge_track_batch'),
    path('duplicates/scan/', scan_duplicates_view, name='scan_duplicates'),
    path('duplicates/merge/', merge_candidate, name='merge_candidate'),
    path('duplicates/dismiss/', dismiss_candidate, name='dismiss_candidate'),
    path('duplicates/auto_merge_certain/', auto_merge_certain, name='auto_merge_certain'),
    path('duplicates/merge_artist_groups/', merge_artist_groups, name='merge_artist_groups'),
    path('manual_transition/', manual_transition, name='manual_transition'),
    path('save_waveform/', save_waveform, name='save_waveform'),
    path('manual_merge_track/', manual_merge_duplicate, name='manual_merge_track'),
    path('manual_merge_artist/', manual_merge_artist, name='manual_merge_artist'),
    # SUGGESTIONS
    path('ajax_suggestions/', ajax_suggestions, name='ajax_suggestions'),
    # CONFIGURATION
    path('config/', config_view, name='config'),
    path('config/reset/', config_reset_view, name='config_reset'),
    # TOOLS
    path('tools/', tools_index, name='tools'),
    # Transitions de sets: PROPOSITIONS (jamais de création auto) + ajout au clic
    path('set_transitions/', set_transitions_view, name='set_transitions'),
    path('set_transitions/add/', add_set_transition, name='add_set_transition'),
    # SETS (historique des sessions)
    path('sets/', display_sets, name='sets_view'),
    # SET BUILDER (graphe de transitions / lookahead) — nouvelle page autonome
    path('set_builder/', set_builder_view, name='set_builder'),
    path('set_builder/graph/<int:track_id>/', set_builder_graph_api, name='set_builder_graph'),
    # UI LAB — bac à sable de concepts UX/UI pour Now Playing (nouvelle page autonome)
    path('ui_lab/', ui_lab_view, name='ui_lab'),
    # PWA — manifest + service worker (installer Now Playing sur le téléphone)
    path('manifest.webmanifest', manifest_view, name='pwa_manifest'),
    path('sw.js', service_worker_view, name='pwa_sw'),
    path('tools/cleanup_musical_keys/', cleanup_musical_keys, name='cleanup_musical_keys'),
    path('tools/cue_points/', cue_points_overview, name='cue_points_overview'),
    path('tools/delete_all_cue_points/', delete_all_cue_points, name='delete_all_cue_points'),
    # REKORDBOX SYNCHRONIZATION
    path('rekordbox/', rekordbox_sync_view, name='rekordbox_sync'),
    path('rekordbox/api/synchronize/', synchronize_rekordbox_collection_api, name='rekordbox_api_synchronize'),
    path('rekordbox/api/stats/', cue_points_stats_api, name='rekordbox_api_stats'),
    path('playlist_favourite/', playlist_favourite.playlist_favourite, name='playlist_favourite'),
    path('toggle_playlist_favourite/', toggle_playlist_favourite, name='toggle_playlist_favourite'),
    path('playlists/', playlist_list_view, name='playlist_list'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

urlpatterns += [
    path('admin/import-musical-keys/', import_musical_keys_view, name='import_musical_keys'),
]
