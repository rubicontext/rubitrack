from django.contrib import admin

#ac
#from adminsortable2.admin import SortableAdminMixin

# Register your models here.
from .models import Artist, Track, Genre, Playlist, TransitionType, Transition, CurrentlyPlaying, Collection


from django.forms import TextInput, Textarea
from django.db import models
from django import forms


#admin.site.register(Artist)
#admin.site.register(Track)
admin.site.register(Genre)
admin.site.register(Playlist)
admin.site.register(Transition)
admin.site.register(TransitionType)
admin.site.register(CurrentlyPlaying)
admin.site.register(Collection)

#class TrackInline(admin.StackedInline):
class TrackInline(admin.TabularInline):
    model = Track
    extra = 1

#class TrackInline(admin.StackedInline):
class TransitionInline(admin.TabularInline):
    model = Transition
    extra = 1
    fk_name = "track_source"
    fields =(
        ('track_destination', 'comment'),
    )
    widgets = {
          'comment': forms.Textarea(attrs={'rows':2, 'cols':2}),
    }

#@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    fieldsets = [
        (None,               {'fields': ['title', 'artist', 'genre']}),
        ('Notes', {'fields': ['ranking', 'comment', 'comment2']}),
        ('Details', {'fields': ['musical_key', 'bpm', 'bitrate', 'playcount', 'date_last_played']}),
    ]
    inlines = [TransitionInline]
    list_display = ('title', 'artist', 'genre', 'bpm', 'is_techno', 'was_added_recently')
    list_filter = ['genre']
    search_fields = ['title', 'artist__name']
    ordering = ['title']

    #def get_queryset(self, request):
    #    return self.model.objects.filter(user = request.user)

class ArtistAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Say my name!',               {'fields': ['name']}),
    ]
    inlines = [TrackInline]

admin.site.register(Track, TrackAdmin)
admin.site.register(Artist, ArtistAdmin)

#custom track admin view 
class CustomTrackTransition(Track):
    class Meta:
        proxy = True


#v2 for resize area
class TransitionForm(forms.ModelForm):
    comment = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3, 'cols': 15}))
    class Meta:
        model = Transition
        exclude = ('comment',)
        widgets = {
          'comment': forms.Textarea(attrs={'rows':2, 'cols':2}),
        }



class CustomTrackTransitionAdmin(TrackAdmin):
    title = 'Add a new transition'
    fieldsets = None
    #form = TransitionForm
    fields =(
        ('title'),
    )
    inlines = [TransitionInline]

admin.site.register(CustomTrackTransition, CustomTrackTransitionAdmin)


