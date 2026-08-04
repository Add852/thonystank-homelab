// Thony Stank Homelab — Service Worker
// Strategy: cache-first for static assets, network-first for pages, offline fallback
const CACHE_NAME = 'thony-stank-v2';
const STATIC_ASSETS = [
  '/',
  '/dashboard',
  '/about',
  '/notes',
  '/static/css/global.css',
  '/static/manifest.json',
  '/static/favicon.svg',
  '/static/icons/pwa/icon-192.png',
  '/static/icons/pwa/icon-512.png',
  'https://cdn.tailwindcss.com',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css'
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

// Activate: clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch: network-first with cache fallback for navigation, cache-first for static
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Don't intercept non-GET requests or browser extensions
  if (event.request.method !== 'GET') return;

  // Skip external CDN script fetches that have their own caching
  if (url.hostname === 'cdn.tailwindcss.com') {
    event.respondWith(caches.match(event.request).then((cached) => cached || fetch(event.request)));
    return;
  }

  // Navigation requests: network-first with offline fallback
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          // Cache a clone of the response
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          return response;
        })
        .catch(() => {
          return caches.match(event.request).then((cached) => {
            if (cached) return cached;
            // Ultimate fallback — return a cached page or simple offline message
            return caches.match('/') || new Response(
              '<html><head><meta charset="UTF-8"><title>Offline - Thony Stank</title>' +
              '<style>body{font-family:-apple-system,sans-serif;display:flex;align-items:center;justify-content:center;' +
              'height:100vh;margin:0;background:#0f172a;color:#e2e8f0;text-align:center}' +
              'h1{font-size:2rem;margin-bottom:0.5rem}</style></head>' +
              '<body><div><h1>📡 Offline</h1><p>No connection. Check back soon.</p></div></body></html>',
              { headers: { 'Content-Type': 'text/html' } }
            );
          });
        })
    );
    return;
  }

  // Static assets: cache-first
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(event.request).then((cached) => {
        if (cached) return cached;
        return fetch(event.request).then((response) => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          return response;
        });
      })
    );
    return;
  }

  // Everything else: network-first, no caching
  event.respondWith(
    fetch(event.request).catch(() => {
      return caches.match(event.request);
    })
  );
});