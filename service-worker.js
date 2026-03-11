const CACHE_NAME = "dress-deals-v2";
const ASSETS = [
  "/",
  "/index.html",
  "/frontend/styles.css",
  "/frontend/app.js",
  "/manifest.webmanifest",
  "/data/deals.json",
  "/icons/icon-192.svg",
  "/icons/icon-512.svg",
  "/reports/daily-deals.md"
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS)));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    )
  );
});

self.addEventListener("fetch", (event) => {
  const requestUrl = new URL(event.request.url);
  const isLiveDataRequest = ["/data/deals.json", "/reports/daily-deals.md"].includes(requestUrl.pathname);

  if (isLiveDataRequest) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, responseClone));
          return response;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cachedResponse) => cachedResponse || fetch(event.request))
  );
});
