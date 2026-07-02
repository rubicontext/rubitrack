# Generated manually to fix missing updated_by field in Config model
#
# Neutralisée : la colonne updated_by est déjà créée par 0003_add_config_model,
# ce AddField faisait échouer toute création de base neuve (duplicate column).
# Cette migration ne servait qu'à réparer une base existante désynchronisée ;
# elle est conservée vide pour ne pas casser l'historique des bases où elle
# est déjà enregistrée comme appliquée.

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("track", "0018_auto_20251104_0824"),
    ]

    operations = []
