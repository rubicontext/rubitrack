from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('track', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Config',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('refresh_interval_currently_playing_ms', models.IntegerField(default=10000, help_text='Refresh interval for currently playing page (milliseconds)')),
                ('refresh_interval_history_editing_ms', models.IntegerField(default=30000, help_text='Refresh interval for history editing page (milliseconds)')),
                ('rubi_icecast_playlist_file', models.CharField(default='/var/log/icecast2/playlist.log', help_text='Path to Icecast playlist log file', max_length=500)),
                ('max_playlist_history_size', models.IntegerField(default=10, help_text='Maximum number of tracks in playlist history')),
                ('max_suggestions_auto_size', models.IntegerField(default=20, help_text='Maximum number of automatic suggestions')),
                ('max_title_length', models.IntegerField(default=20, help_text='Maximum title length for display')),
                ('max_artist_name_length', models.IntegerField(default=20, help_text='Maximum artist name length for display')),
                ('default_bpm', models.FloatField(default=120.0, help_text='Default BPM value for new tracks')),
                ('default_genre', models.CharField(default='Unknown', help_text='Default genre for new tracks', max_length=50)),
                ('max_suggestions', models.IntegerField(default=10, help_text='Maximum number of suggestions returned by API')),
                ('max_playlist_history', models.IntegerField(default=50, help_text='Maximum number of tracks in playlist history')),
                ('max_upload_size_mb', models.IntegerField(default=10, help_text='Maximum file upload size in MB')),
                ('default_comment_size', models.IntegerField(default=60, help_text='Default size for transition comments')),
                ('transition_animation_duration_ms', models.IntegerField(default=300, help_text='Duration of transition animations (milliseconds)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Configuration',
                'verbose_name_plural': 'Configurations',
            },
        ),
    ]
