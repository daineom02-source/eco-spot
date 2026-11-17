// 에코-스팟 오프라인 지원: 앱 화면은 저장해 두고, 대기질·날씨는 항상 최신을 먼저 받아요.
const CACHE = "eco-spot-v2";
const SHELL = ["./", "index.html", "manifest.webmanifest", "icons/icon-192.png", "icons/icon-512.png", "data/air.json", "data/weather.json"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (url.origin !== location.origin) return;
  const live = url.pathname.endsWith("/data/air.json") || url.pathname.endsWith("/data/weather.json") || url.pathname.endsWith("/index.html") || url.pathname.endsWith("/");
  if (live) {
    // 네트워크 우선: 새 버전과 최신 데이터를 먼저 받고, 오프라인이면 저장본 사용
    e.respondWith(fetch(e.request).then(r => { const copy = r.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); return r; })
      .catch(() => caches.match(e.request).then(hit => hit || caches.match("index.html"))));
    return;
  }
  e.respondWith(caches.match(e.request).then(hit => hit || fetch(e.request)));
});
