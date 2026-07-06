"""
PWA — manifest + service worker pour installer Now Playing sur le téléphone.

Servis par Django (plutôt que fichiers statiques) pour garder les chemins
corrects via reverse() et poser les bons en-têtes / scope du service worker.
"""

from django.http import HttpResponse, JsonResponse
from django.templatetags.static import static
from django.urls import reverse


def manifest_view(request):
    """Manifest web app (fiche d'identité de la PWA)."""
    data = {
        "name": "RubiTrack — Now Playing",
        "short_name": "RubiTrack",
        "description": "Ce qui joue et quoi enchaîner, en cabine.",
        "start_url": reverse("currently_playing_view"),
        "scope": "/track/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#ffffff",
        "theme_color": "#283C4F",
        "icons": [
            {"src": static("img/rubitrack-icon-192.png"), "sizes": "192x192", "type": "image/png"},
            {"src": static("img/rubitrack-icon-512.png"), "sizes": "512x512", "type": "image/png"},
            {"src": static("img/rubitrack-icon-maskable.png"), "sizes": "512x512",
             "type": "image/png", "purpose": "maskable"},
        ],
    }
    return JsonResponse(data, content_type="application/manifest+json")


# Service worker: network-first sur la page (données fraîches, fallback cache si
# réseau du lieu KO), cache-first sur les statics. Cache le "dernier état connu"
# pour que l'écran ne devienne jamais blanc en cabine.
_SERVICE_WORKER = """
const CACHE = 'rubitrack-v1';
self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.add('%(start)s')).then(() => self.skipWaiting()));
});
self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((ks) =>
    Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
  ).then(() => self.clients.claim()));
});
self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  if (url.pathname.startsWith('%(page)s')) {
    // network-first: page fraiche si possible, sinon dernier etat en cache
    e.respondWith(
      fetch(e.request).then((r) => {
        const copy = r.clone();
        caches.open(CACHE).then((c) => c.put(e.request, copy));
        return r;
      }).catch(() => caches.match(e.request))
    );
    return;
  }
  // statics: cache-first (rapide, resiste au reseau)
  e.respondWith(caches.match(e.request).then((r) => r || fetch(e.request)));
});
"""


def service_worker_view(request):
    page = reverse("currently_playing_view")
    body = _SERVICE_WORKER % {"start": page, "page": page}
    resp = HttpResponse(body, content_type="application/javascript")
    # autorise le scope /track/ même si le SW est servi ailleurs
    resp["Service-Worker-Allowed"] = "/track/"
    resp["Cache-Control"] = "no-cache"
    return resp
