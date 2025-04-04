from django import forms
from django.shortcuts import render
from django.contrib.auth.decorators import login_required


class ExportCollectionForm(forms.Form):
    original_file = forms.FileField()
    old_path_for_music_folder = forms.CharField(initial='C:\\rubi\\son\\')
    new_path_for_music_folder = forms.CharField(initial='C:\\rubi\\son\\01-Mix-Youtube\\')
    tag_for_transition = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Default: RATING'}))



@login_required
def handle_export_collection(file):
    # print('xml parsing BEGINs')
    xmldoc = xml.dom.minidom.parse(file)
    values = []


@login_required
def export_collection(request):
    if request.method == 'POST':
        form = ExportCollectionForm(request.POST, request.FILES)
        if form.is_valid():
            # do something
            handle_export_collection(file)
            # cptNewTracks, cptExistingTracks = handle_uploaded_file(request.FILES['file'])
            return render(
                request,
                'track/export_collection.html',
                {
                    'form': form,
                    'nb_new_tracks': cptNewTracks,
                    'nb_existing_tracks': cptExistingTracks,
                    'submitted': True,
                },
            )
    else:
        form = ExportCollectionForm()
    return render(request, 'track/export_collection.html', {'form': form})
