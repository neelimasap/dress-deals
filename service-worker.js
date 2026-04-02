const CACHE_NAME = "dress-deals-v7";
const APP_SHELL = [
  "/",
  "/index.html",
  "/frontend/styles.css",
  "/frontend/app.js",
  "/manifest.webmanifest",
  "/icons/icon-192.svg",
  "/icons/icon-512.svg"
];

const NETWORK_FIRST_PATHS = new Set([
  "/",
  "/index.html",
  "/frontend/styles.css",
  "/frontend/app.js",
  "/data/deals.json",
  "/reports/daily-deals.md",
  "/manifest.webmanifest"
]);

async function networkFirst(request) {
  try {
    const response = await fetch(request);
    const cache = await caches.open(CACHE_NAME);
    cache.put(request, response.clone());
    return response;
  } catch {
    return caches.match(request);
  }
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("message", (event) => {
  if (event.data?.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") {
    return;
  }

  const requestUrl = new URL(event.request.url);
  if (requestUrl.origin !== self.location.origin || requestUrl.pathname === "/service-worker.js") {
    return;
  }

  const isNavigation = event.request.mode === "navigate";
  const isNetworkFirst = isNavigation || NETWORK_FIRST_PATHS.has(requestUrl.pathname);

  if (isNetworkFirst) {
    event.respondWith(networkFirst(event.request));
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cachedResponse) => cachedResponse || fetch(event.request))
  );
});
