from django.urls import path
from django.contrib import admin

from . import views
from . import upload_collection

urlpatterns = [
    path('', views.index, name='index'),
    path('uploadcollection/', upload_collection.upload_file, name='upload_collection_view'),
]