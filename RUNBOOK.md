# Rubitrack — redémarrage des services (lula / 193.70.86.101)

Connexion : `ssh ruser@193.70.86.101` (les commandes `systemctl` demandent `sudo`).

## Redémarrage complet, dans l'ordre

```bash
# 1. Base de données (l'app en dépend) — PG16 sur le port 5433
sudo systemctl restart postgresql@16-main

# 2. Application rubitrack (uWSGI venv py3.12)
sudo systemctl restart rubitrack-uwsgi

# 3. Serveur web (HTTPS)
sudo systemctl restart nginx

# 4. Diffusion du mix (source du "Now Playing", port 8059)
sudo systemctl restart icecast2
```

## Vérification (30 s)

```bash
# tous doivent afficher "active"
for s in postgresql@16-main rubitrack-uwsgi nginx icecast2; do
  echo "$s : $(systemctl is-active $s)"; done

# le site répond 200, Icecast écoute sur 8059
curl -s -o /dev/null -w 'site %{http_code}\n' https://track.rubicontext.com/admin/login/
ss -tlnp | grep ':8059' && echo "icecast OK"
```

## Points d'attention

- **rubitrack tourne via `rubitrack-uwsgi.service`, PAS l'emperor uWSGI.** Ne jamais faire `touch` sur un vassal ni recharger l'emperor pour l'app : `systemctl restart rubitrack-uwsgi` uniquement.
- **Logs** app : `/var/log/uwsgi/app/track.log` — Icecast : `/var/log/icecast2/error.log`.
- Tous ces services sont **enabled** → ils redémarrent seuls après un reboot machine.
- `apache2` + `uwsgi` (emperor) = ancienne app *gourmet* (en décom), sans rapport avec rubitrack.
- Base : `rubitrack_dev` sur PG **16** (port **5433**), pas le PG12 (5432).
- Backup quotidien automatique à 3h (cron `ruser`, `~/backups/`).
