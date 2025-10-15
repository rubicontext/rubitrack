from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.forms import ModelForm
from ..models import Config


class ConfigForm(ModelForm):
    class Meta:
        model = Config
        exclude = ['created_at', 'updated_at', 'updated_by']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            if field_name.endswith('_ms'):
                field.widget.attrs['type'] = 'number'
                field.widget.attrs['min'] = '0'
            elif field_name.startswith('max_') and not field_name.endswith('_mb'):
                field.widget.attrs['type'] = 'number'
                field.widget.attrs['min'] = '1'
            elif field_name == 'default_bpm':
                field.widget.attrs['type'] = 'number'
                field.widget.attrs['min'] = '50'
                field.widget.attrs['max'] = '200'
                field.widget.attrs['step'] = '0.1'
            elif field_name in ('default_bpm_range_suggestions','default_musical_key_distance','default_ranking_min',
                                 'currently_bpm_range_suggestions','currently_musical_key_distance','currently_ranking_min'):
                field.widget.attrs['type'] = 'number'
                field.widget.attrs['min'] = '0'
                field.widget.attrs['max'] = '100'
                field.widget.attrs['step'] = '1'


@login_required
def config_view(request):
    """Configuration editing view"""
    config = Config.get_config()
    
    if request.method == 'POST':
        form = ConfigForm(request.POST, instance=config)
        if form.is_valid():
            config_instance = form.save(commit=False)
            config_instance.updated_by = request.user
            config_instance.save()
            messages.success(request, 'Configuration updated successfully!')
            return redirect('config')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ConfigForm(instance=config)
    
    return render(request, 'track/config/config_form.html', {
        'form': form,
        'config': config,
        'title': 'RubiTrack Configuration'
    })


@login_required
def config_reset_view(request):
    """Reset configuration to default values"""
    if request.method == 'POST':
        config = Config.get_config()
        config.refresh_interval_currently_playing_ms = 10000
        config.refresh_interval_history_editing_ms = 30000
        config.rubi_icecast_playlist_file = '/var/log/icecast2/playlist.log'
        config.max_playlist_history_size = 10
        config.max_suggestions_auto_size = 20
        config.default_bpm_range_suggestions = 3
        config.default_musical_key_distance = 3
        config.default_ranking_min = 3
        config.currently_bpm_range_suggestions = 3
        config.currently_musical_key_distance = 4
        config.currently_ranking_min = 1
        config.max_title_length = 20
        config.max_artist_name_length = 20
        config.default_bpm = 120.0
        config.default_genre = "Unknown"
        config.max_suggestions = 10
        config.max_playlist_history = 50
        config.max_upload_size_mb = 10
        config.default_comment_size = 60
        config.transition_animation_duration_ms = 300
        config.updated_by = request.user
        config.save()
        messages.success(request, 'Configuration reset to default values!')
        return redirect('config_view')
    return render(request, 'track/config/config_reset_confirm.html')
