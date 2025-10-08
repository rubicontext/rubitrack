"""
Vues pour les outils d'administration de RubiTrack
"""

import time
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Count

from .models import Track, CuePoint, TrackCuePoints
from .musical_key_utils import extract_musical_key_from_title


@login_required
def tools_index(request):
    """
    Page d'accueil des outils d'administration.
    """
    # Statistiques de la collection
    total_tracks = Track.objects.count()
    tracks_with_keys = Track.objects.exclude(Q(musical_key__isnull=True) | Q(musical_key='')).count()
    tracks_without_keys = total_tracks - tracks_with_keys
    
    # Estimation des clés potentielles dans les titres
    tracks_with_potential_keys = 0
    sample_tracks = Track.objects.all()[:1000]  # Échantillon pour éviter la surcharge
    for track in sample_tracks:
        if track.title and extract_musical_key_from_title(track.title):
            tracks_with_potential_keys += 1
    
    # Extrapolation sur toute la collection
    if sample_tracks.count() > 0:
        potential_keys_in_titles = int((tracks_with_potential_keys / sample_tracks.count()) * total_tracks)
    else:
        potential_keys_in_titles = 0
    
    context = {
        'total_tracks': total_tracks,
        'tracks_with_keys': tracks_with_keys,
        'tracks_without_keys': tracks_without_keys,
        'potential_keys_in_titles': potential_keys_in_titles,
    }
    
    return render(request, 'track/tools/tools_index.html', context)


@login_required
def cleanup_musical_keys(request):
    """
    Page pour nettoyer et normaliser automatiquement les clés musicales.
    Extrait les clés depuis les titres et les normalise sans modifier les titres.
    """
    results = None
    overwrite_existing = request.POST.get('overwrite_existing', False)
    dry_run = request.POST.get('dry_run', False)
    
    if request.method == 'POST':
        results = process_musical_keys_cleanup(overwrite_existing, dry_run)
        
        # Messages utilisateur
        if dry_run:
            messages.info(
                request, 
                f"Mode test : {results['extracted_keys']} clés musicales détectées dans les titres. "
                f"{results['would_update']} tracks seraient mises à jour."
            )
        else:
            if results['updated_tracks'] > 0:
                messages.success(
                    request,
                    f"Nettoyage terminé ! {results['updated_tracks']} tracks mises à jour avec leurs clés musicales normalisées."
                )
            else:
                messages.warning(
                    request,
                    "Aucune track n'a été mise à jour. Vérifiez vos options de nettoyage."
                )
    
    context = {
        'results': results,
        'overwrite_existing': overwrite_existing,
        'dry_run': dry_run,
    }
    
    return render(request, 'track/tools/cleanup_musical_keys.html', context)


def process_musical_keys_cleanup(overwrite_existing, dry_run):
    """
    Traite le nettoyage des clés musicales.
    Fonction séparée pour réduire la complexité cognitive.
    """
    start_time = time.time()
    
    # Configuration du traitement
    overwrite_existing = bool(overwrite_existing)
    dry_run = bool(dry_run)
    
    # Requête de base
    tracks_query = Track.objects.all()
    if not overwrite_existing:
        tracks_query = tracks_query.filter(Q(musical_key__isnull=True) | Q(musical_key=''))
    
    total_tracks = tracks_query.count()
    updated_tracks = 0
    extracted_keys = 0
    skipped_tracks = 0
    would_update = 0
    examples = []
    
    # Traitement par batch
    batch_size = 100
    
    with transaction.atomic():
        for i in range(0, total_tracks, batch_size):
            batch_tracks = tracks_query[i:i+batch_size]
            
            for track in batch_tracks:
                result = process_single_track(track, overwrite_existing, dry_run)
                
                # Accumulation des statistiques
                if result['extracted_key']:
                    extracted_keys += 1
                    
                if result['action'] == 'updated':
                    updated_tracks += 1
                elif result['action'] == 'would_update':
                    would_update += 1
                else:
                    skipped_tracks += 1
                
                # Ajouter aux exemples (limité à 10)
                if len(examples) < 10:
                    examples.append(result)
    
    processing_time = time.time() - start_time
    
    return {
        'total_tracks': total_tracks,
        'updated_tracks': updated_tracks,
        'extracted_keys': extracted_keys,
        'skipped_tracks': skipped_tracks,
        'would_update': would_update,
        'examples': examples,
        'processing_time': processing_time,
    }


def process_single_track(track, overwrite_existing, dry_run):
    """
    Traite une seule track pour l'extraction de clé musicale.
    """
    old_key = track.musical_key
    
    # Extraire la clé depuis le titre
    extracted_key = extract_musical_key_from_title(track.title) if track.title else None
    
    if not extracted_key:
        return {
            'title': track.title,
            'extracted_key': None,
            'old_key': old_key,
            'new_key': old_key,
            'action': 'skipped'
        }
    
    # Décider si on met à jour
    should_update = overwrite_existing or not old_key or old_key.strip() == ''
    
    if should_update:
        action = 'would_update' if dry_run else 'updated'
        
        if not dry_run:
            track.musical_key = extracted_key
            track.save(update_fields=['musical_key'])
        
        return {
            'title': track.title,
            'extracted_key': extracted_key,
            'old_key': old_key,
            'new_key': extracted_key,
            'action': action
        }
    else:
        return {
            'title': track.title,
            'extracted_key': extracted_key,
            'old_key': old_key,
            'new_key': old_key,
            'action': 'skipped'
        }


@login_required
def cue_points_overview(request):
    """
    Vue d'ensemble des cue points de la collection.
    """
    # Statistiques générales
    total_tracks = Track.objects.count()
    tracks_with_cue_points = TrackCuePoints.objects.count()
    total_cue_points = CuePoint.objects.count()
    
    # Tracks avec cue points avec détails
    tracks_with_cue_points_details = []
    for track_cue_points in TrackCuePoints.objects.select_related('track', 'track__artist').all()[:50]:  # Limiter à 50 pour l'affichage
        cue_points_list = track_cue_points.get_cue_points_list()
        tracks_with_cue_points_details.append({
            'track': track_cue_points.track,
            'cue_points_count': len(cue_points_list),
            'cue_points': cue_points_list[:3]  # Afficher seulement les 3 premiers
        })
    
    # Statistiques par type de cue point
    cue_point_types = CuePoint.objects.values('type').annotate(count=Count('type')).order_by('-count')
    
    context = {
        'total_tracks': total_tracks,
        'tracks_with_cue_points': tracks_with_cue_points,
        'total_cue_points': total_cue_points,
        'tracks_with_cue_points_details': tracks_with_cue_points_details,
        'cue_point_types': cue_point_types,
    }
    
    return render(request, 'track/tools/cue_points_overview.html', context)
