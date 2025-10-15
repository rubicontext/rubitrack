from track.models import Track, Config


def get_suggestions_same_artist(track):
    suggestions = None
    if track is not None:
        suggestions = Track.objects.filter(artist=track.artist)
    return suggestions


def get_list_track_suggestions_auto(track):
    """Return automatic suggestions based on currently_* config parameters"""
    if track is None or track.bpm is None:
        return None

    config = Config.get_config()
    bpm_percent = config.currently_bpm_range_suggestions
    key_distance_max = config.currently_musical_key_distance
    min_ranking = config.currently_ranking_min

    base_qs = Track.objects.filter(
        comment__icontains=track.genre,
        bpm__gte=track.bpm * (1 - bpm_percent / 100),
        bpm__lte=track.bpm * (1 + bpm_percent / 100),
        ranking__gte=min_ranking,
    ).exclude(id=track.id)

    if track.musical_key:
        try:
            from ..musical_key.musical_key_utils import get_compatible_keys, normalize_musical_key_notation

            compatible_keys = get_compatible_keys(track.musical_key, key_distance_max) or []
            compatible_keys_clean = [normalize_musical_key_notation(k) for k in compatible_keys if k]
            # Always include original key
            if track.musical_key not in compatible_keys_clean:
                compatible_keys_clean.append(normalize_musical_key_notation(track.musical_key))
            base_qs = base_qs.filter(musical_key__in=compatible_keys_clean)
        except Exception as e:
            # Fallback exact key
            print("Compatible keys error, fallback to exact key:", e)
            base_qs = base_qs.filter(musical_key=track.musical_key)

    list_tracks = base_qs.order_by('bpm')

    # Compute musical key order (Traktor/Camelot) and sort accordingly
    enriched = []
    for t in list_tracks:
        try:
            mk_obj = t.get_musical_key_obj()
            order_val = mk_obj.order if mk_obj else None
        except Exception:
            order_val = None
        setattr(t, 'musical_key_order', order_val)
        enriched.append(t)

    # Sort by musical_key_order then BPM
    enriched.sort(key=lambda x: (x.musical_key_order if x.musical_key_order is not None else 999, x.bpm if x.bpm else 0))

    max_suggestions = config.max_suggestions_auto_size
    if len(enriched) > max_suggestions:
        enriched = enriched[0: max_suggestions - 1]
    return enriched


