// =========================================================
// 💠 LyxNexus Service Worker
// Offline-first strategy with dynamic caching and live status updates
// =========================================================

const CACHE_NAME = 'lyxnexus-static-v2';
const DYNAMIC_CACHE = 'lyxnexus-dynamic-v1';
const OFFLINE_URL = '/offline.html';
const STATIC_ASSETS = ['/', '/main-page', OFFLINE_URL];
const DEBOUNCE_DELAY = 2000;

let onlineStatus = navigator.onLine;
let debounceTimer = null;

// ---------------------------------------------------------
// 🛰️ Utility: Broadcast message to all connected clients
// ---------------------------------------------------------
async function broadcast(type) {
  const clients = await self.clients.matchAll();
  for (const client of clients) {
    client.postMessage({ type });
  }
}

// ---------------------------------------------------------
// ⚙️ INSTALL: Pre-cache essential static assets
// ---------------------------------------------------------
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting(); // activate immediately
});

// ---------------------------------------------------------
// 🧹 ACTIVATE: Clean up old caches & refresh clients
// ---------------------------------------------------------
self.addEventListener('activate', event => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      for (const key of keys) {
        if (![CACHE_NAME, DYNAMIC_CACHE].includes(key)) {
          await caches.delete(key);
        }
      }

      // Force all tabs to update to the new SW
      const clients = await self.clients.matchAll({ type: 'window' });
      for (const client of clients) {
        client.navigate(client.url);
      }
    })()
  );
  self.clients.claim();
});

// ---------------------------------------------------------
// 🌐 FETCH: Network-first with cache fallback
// ---------------------------------------------------------
self.addEventListener('fetch', event => {
  // Only handle GET requests
  if (event.request.method !== 'GET') return;

  const reqUrl = new URL(event.request.url);

  // Handle static pages (cache-first strategy)
  if (STATIC_ASSETS.includes(reqUrl.pathname)) {
    event.respondWith(
      caches.match(event.request).then(cachedResp => {
        const fetchPromise = fetch(event.request)
          .then(networkResp => {
            if (networkResp && networkResp.status === 200) {
              caches.open(CACHE_NAME).then(cache =>
                cache.put(event.request, networkResp.clone())
              );
            }
            return networkResp;
          })
          .catch(() => null);

        return cachedResp || fetchPromise;
      })
    );
    return;
  }

  // Handle dynamic requests (network-first strategy)
  event.respondWith(
    fetch(event.request)
      .then(resp => {
        if (resp && resp.status === 200) {
          const respClone = resp.clone();
          caches.open(DYNAMIC_CACHE).then(cache =>
            cache.put(event.request, respClone)
          );
        }
        updateNetworkStatus(true);
        return resp;
      })
      .catch(() => {
        updateNetworkStatus(false);
        return caches.match(event.request).then(
          resp => resp || caches.match(OFFLINE_URL)
        );
      })
  );
});

// ---------------------------------------------------------
// 🔁 NETWORK STATUS: Debounced online/offline events
// ---------------------------------------------------------
function updateNetworkStatus(status) {
  if (status !== onlineStatus) {
    onlineStatus = status;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      broadcast(status ? 'ONLINE' : 'OFFLINE');
    }, DEBOUNCE_DELAY);
  }
}

// ---------------------------------------------------------
// 📩 MESSAGE HANDLER (optional future use)
// ---------------------------------------------------------
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SHOW_OFFLINE_OVERLAY') {
    // Placeholder for future overlay logic
  }
});
