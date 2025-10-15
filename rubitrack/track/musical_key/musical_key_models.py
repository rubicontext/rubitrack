from django.db import models

class MusicalKey(models.Model):
    musical = models.CharField(max_length=8, unique=True, help_text="Notation musicale traditionnelle, ex: Am")
    camelot = models.CharField(max_length=4, unique=True, help_text="Notation Camelot, ex: 8A")
    open = models.CharField(max_length=4, unique=True, help_text="Notation Open Key, ex: 1m")
    traktor_color = models.CharField(max_length=16, help_text="Couleur Traktor (hex ou nom)")
    order = models.PositiveSmallIntegerField(help_text="Ordre pour le tri Traktor/Camelot")

    def __str__(self):
        return f"{self.musical} ({self.camelot})"

    class Meta:
        ordering = ["order"]
        verbose_name = "Musical Key"
        verbose_name_plural = "Musical Keys"
