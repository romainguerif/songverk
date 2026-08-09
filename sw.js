/* SONGVERK — cache offline.
   Le HTML passe en réseau d'abord : un rafraîchissement avec du réseau donne toujours la dernière version,
   et le cache ne sert que de filet hors ligne. Le reste garde le cache d'abord, c'est immuable ou presque. */
const CACHE = "songverk-v0.5.1";
const ASSETS = ["./", "./index.html", "./manifest.webmanifest", "./icon.svg"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys()
    .then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("message", e => {
  if (e.data === "skip-waiting") self.skipWaiting();
});

const isDoc = req =>
  req.mode === "navigate" ||
  (req.headers.get("accept") || "").includes("text/html");

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;

  if (isDoc(req)) {
    // réseau d'abord, cache en secours
    e.respondWith(
      fetch(req)
        .then(res => {
          // Ne jamais mettre en cache une redirection : derrière Cloudflare Access, une session
          // expirée renvoie la page de connexion, qui remplacerait l'app dans le cache.
          const sameOrigin = res && res.url && new URL(res.url).origin === self.location.origin;
          if (res && res.ok && !res.redirected && sameOrigin) {
            const copy = res.clone();
            caches.open(CACHE).then(c => c.put(req, copy));
          }
          return res;
        })
        .catch(() => caches.match(req).then(hit => hit || caches.match("./index.html")))
    );
    return;
  }

  // cache d'abord, revalidation en arrière-plan
  e.respondWith(caches.match(req).then(hit => {
    const net = fetch(req).then(res => {
      if (res && res.ok) {
        const copy = res.clone();
        caches.open(CACHE).then(c => c.put(req, copy));
      }
      return res;
    }).catch(() => hit);
    return hit || net;
  }));
});
