#!/usr/bin/env python3
"""
Script de test pour vérifier que les constantes sont bien importées et utilisées.
"""

import sys
import os
sys.path.append('/mnt/c/Users/antoine.carnet/work/perso/rubitrack/rubitrack')

try:
    from track.constants import (
        REFRESH_INTERVAL_CURRENTLY_PLAYING_MS,
        REFRESH_INTERVAL_HISTORY_EDITING_MS,
        MAX_TITLE_LENGTH,
        MAX_ARTIST_NAME_LENGTH
    )
    
    print("✅ Import des constantes réussi !")
    print(f"   - Refresh Currently Playing: {REFRESH_INTERVAL_CURRENTLY_PLAYING_MS}ms")
    print(f"   - Refresh History Editing: {REFRESH_INTERVAL_HISTORY_EDITING_MS}ms")
    print(f"   - Max Title Length: {MAX_TITLE_LENGTH}")
    print(f"   - Max Artist Name Length: {MAX_ARTIST_NAME_LENGTH}")
    
except ImportError as e:
    print(f"❌ Erreur d'import: {e}")
    
except Exception as e:
    print(f"❌ Autre erreur: {e}")
