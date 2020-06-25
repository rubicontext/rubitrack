from django.urls import path
from django.contrib import admin

from . import views
from . import upload_collection
from . import currently_playing

urlpatterns = [
    path('', views.index, name='index'),
    path('upload_collection/', upload_collection.upload_file, name='upload_collection_view'),
    path('currently_playing/', currently_playing.display_currently_playing, name='currently_playing_view'),
]