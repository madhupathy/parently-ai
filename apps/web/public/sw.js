// Parently Service Worker — App Shell Cache + Offline Support
const CACHE_NAME = "parently-shell-v1";

// App shell assets to cache on install
const SHELL_ASSETS = [
  "/",
  "/offline",
  "/manifest.json",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
];

// Routes we never try to serve from cache (always go to network)
const NETWORK_ONLY_PATTERNS = [
  /^\/api\//,
  /^\/auth\//,
];

// ── Install: pre-cache app shell ──────────────────────────────────────────────
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(SHELL_ASSETS))
      .then(() => self.skipWaiting())
  );
});

// ── Activate: remove old caches ───────────────────────────────────────────────
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key !== CACHE_NAME)
            .map((key) => caches.delete(key))
        )
      )
      .then(() => self.clients.claim())
  );
});

// ── Fetch: network-first with cache fallback ──────────────────────────────────
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Only handle same-origin GET requests
  if (request.method !== "GET" || url.origin !== self.location.origin) return;

  // API and auth routes: network only — never serve stale data
  if (NETWORK_ONLY_PATTERNS.some((p) => p.test(url.pathname))) {
    event.respondWith(fetch(request));
    return;
  }

  // For navigation requests (HTML pages): network first, cache fallback, offline page
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((response) => {
          // Cache a fresh copy of each page visited
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        })
        .catch(() =>
          caches
            .match(request)
            .then((cached) => cached || caches.match("/offline"))
        )
    );
    return;
  }

  // Static assets: cache first, then network
  event.respondWith(
    caches.match(request).then(
      (cached) =>
        cached ||
        fetch(request).then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        })
    )
  );
});
