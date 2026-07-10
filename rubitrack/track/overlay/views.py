"""
Overlay — mini-vues compactes à poser par-dessus Traktor (petite fenêtre
navigateur + PowerToys Always On Top).

- /track/overlay/  : RÉFÉRENCE — 1 ligne track courante, sections repliables
  (transitions avec commentaire + dernières jouées).
- /track/overlay2/ : BAC À SABLE — comme la référence, plus un bouton « + »
  sur chaque dernière jouée pour créer la transition (jouée -> courante)
  avec saisie du commentaire. Création UNIQUEMENT au clic (jamais auto).
"""

import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from ..models import Config, Track, Transition, TransitionType
from ..currently_playing.currently_playing import (
    get_currently_playing_track,
    get_transitions_after,
)
from ..playlist.playlist_transitions import PLAYLIST_TRANSITION_AUTO_GENERATED

logger = logging.getLogger(__name__)

LAST_PLAYED_COUNT = 3


def _live_pair_counts(track):
    """Compte EN DIRECT, depuis l'historique des sets, combien de fois chaque
    autre track a été enchaînée juste après / juste avant `track`.
    Returns: (after: {track_id: n}, before: {track_id: n})."""
    from ..currently_playing.auto_transitions import _count_consecutive_pairs
    after, before = {}, {}
    for (source_id, destination_id), n in _count_consecutive_pairs().items():
        if source_id == track.id:
            after[destination_id] = n
        if destination_id == track.id:
            before[source_id] = n
    return after, before


def filter_transition_for_overlay(queryset, limit=None, count_of=None):
    """Transitions pour l'overlay, triées par nombre de fois réellement
    enchaînées en set (compteur live via count_of, sinon play_count stocké),
    puis note, puis position.

    Les transitions 'Generated from Playlist : X' passent EN DERNIER: elles
    ne servent que de remplissage si les vraies transitions n'atteignent pas
    la limite (Config.overlay_max_transitions). Retourne une liste."""
    if limit is None:
        limit = Config.get_config().overlay_max_transitions
    if count_of is None:
        def count_of(transition):
            return transition.play_count

    def sort_key(transition):
        return (-count_of(transition), -(transition.ranking or 0), transition.position)

    manual, generated = [], []
    for transition in queryset:
        is_generated = (transition.comment or '').lower().startswith(
            PLAYLIST_TRANSITION_AUTO_GENERATED.lower())
        (generated if is_generated else manual).append(transition)
    manual.sort(key=sort_key)
    generated.sort(key=sort_key)
    return (manual + generated[:max(0, limit - len(manual))])[:limit]


def _context(direction='after'):
    track = get_currently_playing_track(with_refresh=True)
    nexts = []
    if track:
        separator = Config.get_config().separator_track_id
        if direction == 'before':
            queryset = (
                Transition.objects.filter(track_destination=track)
                .exclude(track_source_id=separator)
                .select_related('track_source__artist')
            )
        else:
            queryset = (
                get_transitions_after(track)
                .exclude(track_destination_id=separator)
                .select_related('track_destination__artist')
            )
        # Compteurs LIVE depuis l'historique (pas le play_count stocké):
        # nb de fois où l'autre track a été jouée juste après/avant la courante
        after_counts, before_counts = _live_pair_counts(track)
        counts = before_counts if direction == 'before' else after_counts

        def other_of(transition):
            return transition.track_source if direction == 'before' else transition.track_destination

        def live_count(transition):
            return counts.get(other_of(transition).id, 0)

        for transition in filter_transition_for_overlay(queryset, count_of=live_count):
            other = other_of(transition)
            nexts.append({
                'id': transition.id,
                'title': other.title,
                'artist': other.artist.name if other.artist_id else '',
                'key': other.musical_key or '',
                'color': other.get_musical_key_color(),
                'bpm': other.bpm,
                'play_count': live_count(transition),
                'ranking': transition.ranking,
                'comment': transition.comment or '',
            })
    return {'track': track, 'nexts': nexts, 'direction': direction}


def _last_played(current_track):
    """Les 3 dernières tracks jouées avant la courante (séparateur exclu).
    Indique aussi si la transition (jouée -> courante) existe déjà."""
    from ..models import CurrentlyPlaying
    separator = Config.get_config().separator_track_id
    qs = (
        CurrentlyPlaying.objects.exclude(date_played__isnull=True)
        .exclude(track_id=separator)
        .select_related('track__artist')
        .order_by('-date_played')
    )
    existing = set()
    if current_track:
        existing = set(
            Transition.objects.filter(track_destination=current_track)
            .values_list('track_source_id', flat=True)
        )
    plays = []
    for play in qs[:LAST_PLAYED_COUNT + 3]:   # marge pour sauter la courante
        if current_track and play.track_id == current_track.id and not plays:
            continue                           # saute l'entrée "en cours"
        track = play.track
        plays.append({
            'id': track.id,
            'title': track.title,
            'artist': track.artist.name if track.artist_id else '',
            'key': track.musical_key or '',
            'color': track.get_musical_key_color(),
            'bpm': track.bpm,
            'time': play.date_played,
            'has_transition': track.id in existing,
        })
        if len(plays) >= LAST_PLAYED_COUNT:
            break
    return plays


def _direction(request):
    return 'before' if request.GET.get('dir') == 'before' else 'after'


@login_required
def overlay_view(request):
    """Référence: 1 ligne courante + sections repliables."""
    context = _context(direction=_direction(request))
    context['last_played'] = _last_played(context['track'])
    if request.GET.get('partial'):
        return render(request, 'track/overlay/_overlay_content.html', context)
    return render(request, 'track/overlay/overlay.html', context)


@login_required
def overlay2_view(request):
    """Bac à sable: + ajout de transition (jouée -> courante) avec commentaire."""
    context = _context(direction=_direction(request))
    context['last_played'] = _last_played(context['track'])
    if request.GET.get('partial'):
        return render(request, 'track/overlay/_overlay2_content.html', context)
    return render(request, 'track/overlay/overlay2.html', context)


@login_required
@require_POST
def overlay_add_transition(request):
    """Crée (au clic explicite) la transition source -> destination avec
    commentaire saisi. Si elle existe déjà: met à jour le commentaire."""
    source_id = request.POST.get('source_id')
    destination_id = request.POST.get('destination_id')
    comment = (request.POST.get('comment') or '').strip()
    try:
        source = Track.objects.get(id=source_id)
        destination = Track.objects.get(id=destination_id)
    except (Track.DoesNotExist, ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'track introuvable'}, status=404)
    if source.id == destination.id:
        return JsonResponse({'ok': False, 'error': 'même track'}, status=400)

    transition, created = Transition.objects.get_or_create(
        track_source=source,
        track_destination=destination,
        defaults={
            'comment': comment or 'Ajoutée depuis l’overlay',
            'transition_type': TransitionType.objects.filter(id=1).first(),
        },
    )
    if not created and comment:
        transition.comment = comment
        transition.save(update_fields=['comment'])
    logger.info("Overlay: transition %s -> %s (%s)", source.title, destination.title,
                'créée' if created else 'commentaire mis à jour')
    return JsonResponse({'ok': True, 'created': created})


@login_required
@require_POST
def overlay_edit_transition(request):
    """Édite le commentaire d'une transition existante, ou la supprime.
    Action explicite depuis la popin de l'overlay (jamais automatique)."""
    action = request.POST.get('action')
    try:
        transition = Transition.objects.get(id=request.POST.get('transition_id'))
    except (Transition.DoesNotExist, ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'transition introuvable'}, status=404)

    if action == 'delete':
        logger.info("Overlay: transition supprimée %s -> %s",
                    transition.track_source.title, transition.track_destination.title)
        transition.delete()
        return JsonResponse({'ok': True, 'action': 'deleted'})

    transition.comment = (request.POST.get('comment') or '').strip()
    transition.save(update_fields=['comment'])
    logger.info("Overlay: commentaire édité %s -> %s",
                transition.track_source.title, transition.track_destination.title)
    return JsonResponse({'ok': True, 'action': 'saved'})
