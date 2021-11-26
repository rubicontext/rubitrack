from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse

def index(request):
    return HttpResponse("Hello, world. You're at the TRACKS index.")

# def history_playing(request, trackId):
#     currentTrack = Track.objects.get(id=trackId)
#     return redirect('index')

