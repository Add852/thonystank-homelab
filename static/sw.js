// Thony Stank Homelab — Service Worker
// Network-first for everything (deploys appear immediately), cache as offline
// fallback so the PWA still works when the network is down.
const CACHE_NAME = 'thony-stank-v6';
const STATIC_ASSETS = [
  '/',
  '/about',
  '/notes',
  '/static/css/global.css?v=5',
  '/static/css/fontawesome/all.min.css',
  '/static/js/tailwind.js',
  '/static/manifest.json',
  '/static/favicon.svg',
  '/static/icons/pwa/icon-192.png',
  '/static/icons/pwa/icon-512.png'
];

// Install: pre-cache core static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS).catch((err) => {
        // Don't fail install if some assets are unavailable
        console.warn('SW install: some assets failed to cache', err);
      });
    }).then(() => self.skipWaiting())
  );
});

// Activate: clean old caches; on upgrade, reload open tabs so they drop stale assets
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      const old = keys.filter((key) => key !== CACHE_NAME);
      return Promise.all(old.map((key) => caches.delete(key))).then(() => {
        if (old.length) {
          return self.clients.matchAll({ type: 'window' }).then((clients) =>
            clients.forEach((client) => client.navigate(client.url))
          );
        }
      });
    }).then(() => self.clients.claim())
  );
});

// Fetch: network-first with cache fallback (all requests, any origin path)
self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // Cache successful same-origin pages + static so offline still works
        const url = new URL(event.request.url);
        if (response.ok && (url.pathname.startsWith('/static/') || event.request.mode === 'navigate')) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return response;
      })
      .catch(() => {
        return caches.match(event.request).then((cached) => {
          if (cached) return cached;
          if (event.request.mode === 'navigate') {
            return caches.match('/').then((home) => home || new Response(
              '<html><head><meta charset="UTF-8"><title>Offline - Thony Stank</title>' +
              '<style>body{font-family:monospace;display:flex;align-items:center;justify-content:center;' +
              'height:100vh;margin:0;background:#0f172a;color:#e2e8f0;text-align:center}' +
              'h1{font-size:2rem;margin-bottom:0.5rem}</style></head>' +
              '<body><div><h1>\u{1F4E1} Offline</h1><p>No connection. Check back soon.</p></div></body></html>',
              { headers: { 'Content-Type': 'text/html' } }
            ));
          }
          return Response.error();
        });
      })
  );
});
