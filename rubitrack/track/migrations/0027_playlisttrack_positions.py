# Remplace le champ texte Playlist.track_ids (liste Python sérialisée) par un
# modèle de liaison PlaylistTrack avec position, en réutilisant la table M2M
# existante track_playlist_tracks.

import ast

import django.db.models.deletion
from django.db import migrations, models


def populate_positions(apps, schema_editor):
    """Reporte l'ordre stocké dans track_ids sur PlaylistTrack.position.
    Les lignes non listées dans track_ids sont placées à la fin (ordre d'id)."""
    Playlist = apps.get_model('track', 'Playlist')
    PlaylistTrack = apps.get_model('track', 'PlaylistTrack')

    for playlist in Playlist.objects.all():
        order = {}
        if playlist.track_ids:
            try:
                ids = ast.literal_eval(playlist.track_ids)
                if isinstance(ids, list):
                    for tid in ids:
                        if tid not in order:
                            order[tid] = len(order)
            except (ValueError, SyntaxError):
                pass

        rows = list(PlaylistTrack.objects.filter(playlist=playlist))
        known = [r for r in rows if r.track_id in order]
        unknown = sorted(
            (r for r in rows if r.track_id not in order), key=lambda r: r.id
        )
        for row in known:
            row.position = order[row.track_id]
        for i, row in enumerate(unknown):
            row.position = len(order) + i
        if rows:
            PlaylistTrack.objects.bulk_update(rows, ['position'])


class Migration(migrations.Migration):

    dependencies = [
        ('track', '0026_track_playtime_alter_track_audio_id_and_more'),
    ]

    operations = [
        # 1. Mapper la table M2M existante sur le nouveau modèle through
        #    (aucune opération en base: la table track_playlist_tracks et sa
        #    contrainte d'unicité (playlist, track) existent déjà)
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='PlaylistTrack',
                    fields=[
                        ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('playlist', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='playlist_tracks', to='track.playlist')),
                        ('track', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='playlist_entries', to='track.track')),
                    ],
                    options={'db_table': 'track_playlist_tracks'},
                ),
                migrations.AlterField(
                    model_name='playlist',
                    name='tracks',
                    field=models.ManyToManyField(through='track.PlaylistTrack', to='track.track'),
                ),
                migrations.AddConstraint(
                    model_name='playlisttrack',
                    constraint=models.UniqueConstraint(fields=('playlist', 'track'), name='unique_playlist_track'),
                ),
            ],
            database_operations=[],
        ),
        # 2. Colonne position (réelle) puis reprise de l'ordre depuis track_ids
        migrations.AddField(
            model_name='playlisttrack',
            name='position',
            field=models.PositiveIntegerField(default=0),
            preserve_default=False,
        ),
        migrations.RunPython(populate_positions, migrations.RunPython.noop),
        # 3. Suppression de l'ancien champ texte
        migrations.RemoveField(model_name='playlist', name='track_ids'),
        # 4. Alignement sur l'état final du modèle
        migrations.AlterField(
            model_name='playlisttrack',
            name='position',
            field=models.PositiveIntegerField(),
        ),
        migrations.AlterModelOptions(
            name='playlisttrack',
            options={'ordering': ['position']},
        ),
        migrations.AlterModelTable(name='playlisttrack', table=None),
        migrations.AddIndex(
            model_name='playlisttrack',
            index=models.Index(fields=['playlist', 'position'], name='track_playl_playlis_pos_idx'),
        ),
    ]
