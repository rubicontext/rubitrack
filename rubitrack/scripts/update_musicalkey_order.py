from track.models_musicalkey import MusicalKey

# Mapping officiel Traktor : (notation musicale, notation Camelot, ordre)
TRAKTOR_CAMELOT_ORDER = [
    ('Am', '8A'),  # 1
    ('C', '8B'),   # 2
    ('Em', '9A'),  # 3
    ('G', '9B'),   # 4
    ('Bm', '10A'), # 5
    ('D', '10B'),  # 6
    ('F#m', '11A'),# 7
    ('A', '11B'),  # 8
    ('C#m', '12A'),# 9
    ('E', '12B'),  # 10
    ('Abm', '1A'), # 11
    ('B', '1B'),   # 12
    ('Ebm', '2A'), # 13
    ('F#', '2B'),  # 14
    ('Bbm', '3A'), # 15
    ('Db', '3B'),  # 16
    ('Fm', '4A'),  # 17
    ('Ab', '4B'),  # 18
    ('Cm', '5A'),  # 19
    ('Eb', '5B'),  # 20
    ('Gm', '6A'),  # 21
    ('Bb', '6B'),  # 22
    ('Dm', '7A'),  # 23
    ('F', '7B'),   # 24
]

for idx, (musical, camelot) in enumerate(TRAKTOR_CAMELOT_ORDER, start=1):
    key_obj = MusicalKey.objects.filter(musical=musical).first()
    if key_obj:
        key_obj.order = idx
        key_obj.camelot = camelot
        key_obj.save()
        print(f"Updated: {musical} ({camelot}) => order {idx}")
    else:
        print(f"Not found in DB: {musical} ({camelot})")
print("Mise à jour terminée.")
