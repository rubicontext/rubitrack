# Migration du modèle cue points : les 8 colonnes cue_point_1..8 de
# TrackCuePoints deviennent une relation CuePoint(track, slot).

import django.db.models.deletion
from django.db import migrations, models


def populate_track_and_slot(apps, schema_editor):
    """Reporte track/slot sur chaque CuePoint depuis TrackCuePoints,
    puis supprime les CuePoint orphelins (non référencés par un slot)."""
    TrackCuePoints = apps.get_model('track', 'TrackCuePoints')
    CuePoint = apps.get_model('track', 'CuePoint')

    used_ids = set()
    for tcp in TrackCuePoints.objects.all():
        for i in range(1, 9):
            cp_id = getattr(tcp, f'cue_point_{i}_id')
            if cp_id:
                CuePoint.objects.filter(id=cp_id).update(track=tcp.track_id, slot=i)
                used_ids.add(cp_id)
    CuePoint.objects.exclude(id__in=used_ids).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('track', '0024_config_separator_track_id'),
    ]

    operations = [
        # 1. Champs nullable le temps de la migration de données
        migrations.AddField(
            model_name='cuepoint',
            name='track',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='new_cue_points',
                to='track.track',
            ),
        ),
        migrations.AddField(
            model_name='cuepoint',
            name='slot',
            field=models.PositiveSmallIntegerField(
                null=True,
                help_text='Slot 1-8 (RCueN, Traktor HOTCUE = slot - 1)',
            ),
        ),
        # 2. Reprise des données depuis les 8 colonnes
        migrations.RunPython(populate_track_and_slot, migrations.RunPython.noop),
        # 3. Suppression de l'ancien modèle (libère le related_name 'cue_points')
        migrations.DeleteModel(name='TrackCuePoints'),
        # 4. Resserrage : non-null + related_name définitif + contrainte d'unicité
        migrations.AlterField(
            model_name='cuepoint',
            name='track',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='cue_points',
                to='track.track',
            ),
        ),
        migrations.AlterField(
            model_name='cuepoint',
            name='slot',
            field=models.PositiveSmallIntegerField(
                help_text='Slot 1-8 (RCueN, Traktor HOTCUE = slot - 1)',
            ),
        ),
        migrations.AlterModelOptions(
            name='cuepoint',
            options={
                'ordering': ['slot'],
                'verbose_name': 'Cue Point',
                'verbose_name_plural': 'Cue Points',
            },
        ),
        migrations.AddConstraint(
            model_name='cuepoint',
            constraint=models.UniqueConstraint(
                fields=('track', 'slot'), name='unique_cuepoint_track_slot'
            ),
        ),
    ]
