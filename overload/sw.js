/* Offline cache. Each version stores every file at install, in one go, and the app is served from that copy.
   A new version installs next to the old one and takes over on the next launch, so old and new files never mix.
   CACHE and ASSETS are written by `npm run stamp`; a test fails if they're out of date. */
const CACHE = 'overload-7069a0fc6e';
const ASSETS = [
  './', 'index.html', 'manifest.webmanifest', 'css/app.css', 'icons/icon-180.png', 'icons/icon-192.png',
  'icons/icon-512.png', 'icons/icon.svg', 'js/app.js', 'js/bodymap.js', 'js/chart.js', 'js/dataio.js', 'js/icons.js',
  'js/library.js', 'js/parse.js', 'js/planner.js', 'js/screens/body.js', 'js/screens/common.js',
  'js/screens/exercise.js', 'js/screens/exercises.js', 'js/screens/flow.js', 'js/screens/home.js',
  'js/screens/sessions.js', 'js/screens/setentry.js', 'js/screens/settings.js', 'js/screens/today.js', 'js/smart.js',
  'js/stats.js', 'js/store.js', 'js/timer.js', 'js/ui.js', 'js/util.js',
];

self.addEventListener('install', e => {
  // 'reload' skips the browser's HTTP cache, so a new version never stores stale files.
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS.map(u => new Request(u, { cache: 'reload' })))).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  // Other apps can share this origin (e.g. several GitHub Pages projects), so only remove our own old versions.
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k.startsWith('overload-') && k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET' || new URL(e.request.url).origin !== location.origin) return;
  e.respondWith(caches.open(CACHE).then(c => c.match(e.request, { ignoreSearch: true, ignoreVary: true })).then(hit => hit || fetch(e.request)));
});
