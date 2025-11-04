
const CACHE_NAME = 'lyxnexus-static-v2';
const DYNAMIC_CACHE = 'lyxnexus-dynamic-v1';
const OFFLINE_URL = '/offline.html';
const STATIC_ASSETS = ['/', '/main-page', OFFLINE_URL];
const DEBOUNCE_DELAY = 2000;

let onlineStatus = navigator.onLine;
let debounceTimer = null;

async function broadcast(type) {
  const clients = await self.clients.matchAll();
  for (const client of clients) {
    client.postMessage({ type });
  }
}

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting(); // activate immediately
});

self.addEventListener('activate', event => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      for (const key of keys) {
        if (![CACHE_NAME, DYNAMIC_CACHE].includes(key)) {
          await caches.delete(key);
        }
      }

      const clients = await self.clients.matchAll({ type: 'window' });
      for (const client of clients) {
        client.navigate(client.url);
      }
    })()
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;

  const reqUrl = new URL(event.request.url);

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

function updateNetworkStatus(status) {
  if (status !== onlineStatus) {
    onlineStatus = status;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      broadcast(status ? 'ONLINE' : 'OFFLINE');
    }, DEBOUNCE_DELAY);
  }
}

self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SHOW_OFFLINE_OVERLAY') {
  }
});
// --- PUSH NOTIFICATION HANDLER (added) ---
self.addEventListener("push", (event) => {
  if (!event.data) return;
  const data = event.data.json();

  const title = data.title || "LyxNexus";
  const body = data.body || data.message || "You have a new notification.";
  const icon = data.icon || "/uploads/favicon-1.png";

  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      icon,
      badge: icon,
      data: data,
      tag: data.tag || "lyxnexus-general"
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const targetUrl = event.notification.data?.url || "/";
  event.waitUntil(
    clients.matchAll({ type: "window" }).then((clientList) => {
      for (const client of clientList) {
        if (client.url === targetUrl && "focus" in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) return clients.openWindow(targetUrl);
    })
  );
});
