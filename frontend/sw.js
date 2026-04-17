const CACHE_NAME = "integra-saas-v1";
const ASSETS_TO_CACHE = [
    "/",
    "/dashboard",
    "/login",
    "/css/style.css",
    "/js/core/settings.js",
    "/js/core/supabase-client.js",
    "/js/core/script.js"
];

// Install event: cache static assets
self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log("[ServiceWorker] Caching core assets");
            return cache.addAll(ASSETS_TO_CACHE);
        })
    );
});

// Activate event: clean up old caches
self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((keyList) => {
            return Promise.all(
                keyList.map((key) => {
                    if (key !== CACHE_NAME) {
                        console.log("[ServiceWorker] Removing old cache", key);
                        return caches.delete(key);
                    }
                })
            );
        })
    );
    return self.clients.claim();
});

// Fetch event: Network first, then cache fallback
self.addEventListener("fetch", (event) => {
    // Only cache GET requests
    if (event.request.method !== "GET") return;
    
    // Skip API calls from being cached by SW
    if (event.request.url.includes("/api/")) return;

    event.respondWith(
        fetch(event.request).catch(() => {
            return caches.match(event.request);
        })
    );
});
