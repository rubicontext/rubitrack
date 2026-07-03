from django.core.management.base import BaseCommand

from track.currently_playing.auto_transitions import detect_transitions_from_history


class Command(BaseCommand):
    help = "Détecte les transitions récurrentes dans l'historique de lecture (sets)"

    def handle(self, *args, **options):
        stats = detect_transitions_from_history()
        self.stdout.write(self.style.SUCCESS(
            f"{stats['created']} transitions créées — {stats['recurring']} enchaînements "
            f"récurrents ({stats['already_known']} déjà connus) sur {stats['pairs_seen']} paires"
        ))
