/* Offline cache: serve the app shell from cache, refresh it in the background. */
const CACHE = 'overload-v1';
const ASSETS = [
  './', 'index.html', 'manifest.webmanifest', 'css/app.css', 'icons/icon.svg', 'icons/icon-180.png', 'icons/icon-192.png', 'icons/icon-512.png',
  'js/app.js', 'js/util.js', 'js/stats.js', 'js/library.js', 'js/planner.js', 'js/store.js', 'js/dataio.js', 'js/icons.js',
  'js/bodymap.js', 'js/chart.js', 'js/ui.js', 'js/timer.js',
  'js/screens/common.js', 'js/screens/home.js', 'js/screens/exercises.js', 'js/screens/exercise.js', 'js/screens/setentry.js',
  'js/screens/sessions.js', 'js/screens/body.js', 'js/screens/today.js', 'js/screens/settings.js',
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET' || new URL(e.request.url).origin !== location.origin) return;
  e.respondWith(caches.open(CACHE).then(async cache => {
    const hit = await cache.match(e.request, { ignoreSearch: true });
    const fresh = fetch(e.request).then(res => { if (res.ok) cache.put(e.request, res.clone()); return res; }).catch(() => hit);
    return hit || fresh;
  }));
});
