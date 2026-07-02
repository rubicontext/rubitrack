from django.shortcuts import render, redirect
from ..models import Track
from django import forms
from .manual_merge_duplicate import merge_duplicate_tracks
import logging

logger = logging.getLogger(__name__)

class ManualMergeForm(forms.Form):
    track_a = forms.ModelChoiceField(queryset=Track.objects.all().order_by('title'), label="Track à garder (A)")
    track_b = forms.ModelChoiceField(queryset=Track.objects.all().order_by('title'), label="Track à supprimer (B)")

# Mapping des tonalités enharmoniques équivalentes (bémols <-> dièses)
ENHARMONIC_EQUIVALENTS = {
    'A#': 'Bb', 'Bb': 'A#',
    'A#m': 'Bbm', 'Bbm': 'A#m',
    'C#': 'Db', 'Db': 'C#',
    'C#m': 'Dbm', 'Dbm': 'C#m',
    'D#': 'Eb', 'Eb': 'D#',
    'D#m': 'Ebm', 'Ebm': 'D#m',
    'F#': 'Gb', 'Gb': 'F#',
    'F#m': 'Gbm', 'Gbm': 'F#m',
    'G#': 'Ab', 'Ab': 'G#',
    'G#m': 'Abm', 'Abm': 'G#m',
}


def normalize_key_enharmonic(key: str) -> str:
    """Normalise une tonalité vers sa forme canonique (dièse préféré au bémol)."""
    if not key:
        return key
    return ENHARMONIC_EQUIVALENTS.get(key, key)


def keys_are_equivalent(key_a: str, key_b: str) -> bool:
    """Retourne True si deux tonalités sont enharmoniquement équivalentes."""
    if not key_a or not key_b:
        return False
    return normalize_key_enharmonic(key_a) == normalize_key_enharmonic(key_b)


def find_duplicate_tracks():
    tracks = Track.objects.all().order_by('title').reverse()
    duplicates = []
    
    # Détection classique : titres identiques après strip (espace en début/fin)
    for track in tracks:
        title_a = track.title.strip()
        others = Track.objects.filter(artist=track.artist).exclude(id=track.id)
        for other in others:
            title_b = other.title.strip()
            # Cas 1 : titres identiques après strip
            if title_a == title_b or (len(title_a) > len(title_b) and title_b in title_a):
                pair = (track, other)
                if (other, track) not in duplicates and pair not in duplicates:
                    duplicates.append(pair)
            # Cas 2 : B = le plus court, et A.title contient B.title
            elif len(title_b) > len(title_a) and title_a in title_b:
                pair = (other, track)
                if (track, other) not in duplicates and pair not in duplicates:
                    duplicates.append(pair)

    # Détection titres identiques hors musical_key "Smoke Out - Fm - 6" vs "Smoke Out - Am - 6"
    # Inclut les cas enharmoniques : "Smoke Out - Bbm - 6" vs "Smoke Out - A#m - 6"
    for track in tracks:
        title_a = track.title.strip()
        parts_a = title_a.split(' - ')
        base_title_a = ' - '.join(parts_a[:-2]) if len(parts_a) >= 3 else (' - '.join(parts_a[:-1]) if len(parts_a) >= 2 else title_a)
        others = Track.objects.filter(artist=track.artist).exclude(id=track.id)
        for other in others:
            title_b = other.title.strip()
            parts_b = title_b.split(' - ')
            base_title_b = ' - '.join(parts_b[:-2]) if len(parts_b) >= 3 else (' - '.join(parts_b[:-1]) if len(parts_b) >= 2 else title_b)
            if base_title_a == base_title_b:
                # Doublons avec tonalités différentes (y compris enharmoniques)
                key_a = track.musical_key or ''
                key_b = other.musical_key or ''
                if key_a != key_b and not keys_are_equivalent(key_a, key_b):
                    pair = (track, other)
                    if (other, track) not in duplicates and pair not in duplicates:
                        duplicates.append(pair)
                # Cas enharmonique : même tonalité mais notation différente (Bbm vs A#m)
                elif keys_are_equivalent(key_a, key_b) and key_a != key_b:
                    pair = (track, other)
                    if (other, track) not in duplicates and pair not in duplicates:
                        duplicates.append(pair)
    return duplicates


def display_duplicates(request):
    # Fonction pour le menu principal des duplicatas
    return render(request, 'track/duplicates/duplicates.html')


def manual_merge_track_batch(request):
    # Fonction pour la page de batch merge avec la liste complète des duplicatas
    duplicates = find_duplicate_tracks()
    return render(request, 'track/duplicates/manual_merge_track_batch.html', {'duplicates': duplicates})


def merge_tracks(request):
    if request.method == "POST":
        id_a = int(request.POST.get("track_a_id"))
        id_b = int(request.POST.get("track_b_id"))
        merge_duplicate_tracks(id_a, id_b)
        return redirect("manual_merge_track_batch")
    return redirect("manual_merge_track_batch")


def bulk_merge_tracks(request):
    if request.method == "POST":
        merge_pairs = request.POST.getlist("merge_pairs")
        if merge_pairs:
            merged_count = 0
            for pair in merge_pairs:
                try:
                    track_a_id, track_b_id = pair.split(',')
                    merge_duplicate_tracks(int(track_a_id), int(track_b_id))
                    merged_count += 1
                except (ValueError, Track.DoesNotExist) as e:
                    logger.warning(f"Erreur lors du merge de la paire {pair}: {e}")
            logger.info(f"Merged {merged_count} paires de tracks")
        return redirect("manual_merge_track_batch")
    return redirect("manual_merge_track_batch")
