/* Minimal offline shell. API calls are never cached: a stale digest presented as
   today's would be worse than no digest. */
const CACHE = 'reboot-shell-v1';
const SHELL = ['/', '/static/styles.css', '/static/app.js', '/static/icon.svg', '/manifest.webmanifest'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((keys) =>
    Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  if (url.pathname.startsWith('/api/')) return;           // always live
  e.respondWith(caches.match(e.request).then((hit) => hit || fetch(e.request)));
});
