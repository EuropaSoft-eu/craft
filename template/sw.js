// Service worker : rend l'application installable et utilisable hors connexion après un premier chargement.
// Pages et chargeurs : réseau d'abord (pour recevoir les mises à jour), cache en secours.
// Fichiers à empreinte (.wasm, .js, morceaux) : cache d'abord, ils ne changent jamais sous le même nom.
const CACHE = "{{CACHE}}";
// Pour la page d'accueil : ne pas intercepter les apps des sous-dossiers, elles ont leur propre service worker
const ROOT_ONLY = {{ROOT_ONLY}};
const SCOPE = new URL(self.registration.scope).pathname;

self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const prefix = CACHE.split("@")[0] + "@";
    for (const key of await caches.keys()) {
      if (key.startsWith(prefix) && key !== CACHE) await caches.delete(key);
    }
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET" || new URL(request.url).origin !== self.location.origin) return;
  const path = new URL(request.url).pathname;
  if (ROOT_ONLY && path.slice(SCOPE.length).includes("/")) return;
  const immutable = /[-_][0-9a-f]{16}(_bg)?\.(wasm|js)$|\.part-[a-z]+$|\.(woff2?|ttf|otf)$/.test(path);

  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    if (immutable) {
      const hit = await cache.match(request);
      if (hit) return hit;
      const response = await fetch(request);
      if (response.ok) cache.put(request, response.clone());
      return response;
    }
    try {
      const response = await fetch(request);
      if (response.ok) cache.put(request, response.clone());
      return response;
    } catch (error) {
      const hit = await cache.match(request, { ignoreSearch: true });
      if (hit) return hit;
      throw error;
    }
  })());
});
