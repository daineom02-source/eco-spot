// 에코-스팟 오프라인 지원: 앱 화면은 저장해 두고, 대기질은 항상 최신을 먼저 받아요.
const CACHE = "eco-spot-v1";
const SHELL = ["./", "index.html", "manifest.webmanifest", "icons/icon-192.png", "icons/icon-512.png", "data/air.json"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (url.origin !== location.origin) return;
  if (url.pathname.endsWith("/data/air.json")) {
    e.respondWith(fetch(e.request).then(r => { const copy = r.clone(); caches.open(CACHE).then(c => c.put("data/air.json", copy)); return r; })
      .catch(() => caches.match("data/air.json")));
    return;
  }
  e.respondWith(caches.match(e.request).then(hit => hit || fetch(e.request).catch(() => caches.match("index.html"))));
});
