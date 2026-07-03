from django.core.management.base import BaseCommand

from track.duplicate.detection import scan_duplicates


class Command(BaseCommand):
    help = "Scanne la collection et alimente les candidats de doublons (DuplicateCandidate)"

    def handle(self, *args, **options):
        stats = scan_duplicates()
        self.stdout.write(self.style.SUCCESS(
            f"Scan terminé: {stats['total_found']} paires "
            f"({stats['created']} créées, {stats['updated']} mises à jour, "
            f"{stats['skipped_memory']} en mémoire dismissed/merged)"
        ))
