from django.urls import path
from django.contrib import admin

from . import views
from . import import_collection, export_collection
from . import currently_playing

urlpatterns = [
    path('', views.index, name='index'),
    path('import_collection/', import_collection.upload_file, name='import_collection_view'),
    path('export_collection/', export_collection.export_collection, name='export_collection_view'),

    path('currently_playing/', currently_playing.display_currently_playing, name='currently_playing_view'),

    path('get_more_played_history_row/', currently_playing.get_more_played_history_row, name='get_more_played_history_row'),
    path('get_more_playlist_history_table/', currently_playing.get_more_playlist_history_table, name='get_more_playlist_history_table'),
    path('get_more_currently_playing_title_block/', currently_playing.get_more_currently_playing_title_block, name='get_more_currently_playing_title_block'),
    path('get_more_currently_playing_track_block/', currently_playing.get_more_currently_playing_track_block, name='get_more_currently_playing_track_block'),
]
