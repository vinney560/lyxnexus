const CACHE_NAME = 'lyxnexus-static-v3';
const DYNAMIC_CACHE = 'lyxnexus-dynamic-v2';
const OFFLINE_URL = '/offline.html';

const STATIC_ASSETS = [
  '/',
  '/login',
  '/main_page',
  '/offline.html',
  '/uploads/favicon-1.png',
  '/uploads/notify.mp3',
  '/static/css/tailwind.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'
];

const DEBOUNCE_DELAY = 2000;
let onlineStatus = navigator.onLine;
let debounceTimer = null;

/* ------------------ Utility: Broadcast Messages ------------------ */
async function broadcast(type, payload = {}) {
  const clients = await self.clients.matchAll({ includeUncontrolled: true });
  for (const client of clients) {
    client.postMessage({ type, ...payload });
  }
}

/* ------------------ Install: Precache core assets ------------------ */
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(STATIC_ASSETS))
      .then(() => self.skipWaiting())
  );
});

/* ------------------ Activate: Clean old caches ------------------ */
self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    for (const key of keys) {
      if (![CACHE_NAME, DYNAMIC_CACHE].includes(key)) {
        await caches.delete(key);
      }
    }

    // Refresh open clients after activation
    const clients = await self.clients.matchAll({ type: 'window' });
    for (const client of clients) {
      client.navigate(client.url);
    }
  })());
  self.clients.claim();
});

/* ------------------ Fetch: Cache-first + Network fallback ------------------ */
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;

  const reqUrl = new URL(event.request.url);

  // Serve static assets from cache first
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

  // For dynamic requests
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

/* ------------------ Connectivity Feedback ------------------ */
function updateNetworkStatus(status) {
  if (status !== onlineStatus) {
    onlineStatus = status;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      broadcast(status ? 'ONLINE' : 'OFFLINE');
    }, DEBOUNCE_DELAY);
  }
}

/* ------------------ Push Notifications ------------------ */
self.addEventListener('push', event => {
  if (!event.data) return;

  const data = event.data.json();
  const title = data.title || '🔔 LyxNexus';
  const body = data.body || data.message || 'You have a new notification.';
  const icon = data.icon || '/uploads/favicon-1.png';
  const tag = data.tag || `lyxnexus-${Date.now()}`;
  const clickUrl = data.url || '/';

  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      icon,
      badge: icon,
      data: { ...data, url: clickUrl },
      tag
    })
  );

  broadcast('PUSH_RECEIVED', { title, body });
});

/* ------------------ Notification Click Behavior ------------------ */
self.addEventListener('notificationclick', event => {
  event.notification.close();
  const targetUrl = event.notification.data?.url || '/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(clientList => {
      for (const client of clientList) {
        if (client.url === targetUrl && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) return clients.openWindow(targetUrl);
    })
  );
});

/* ------------------ Messaging From Client Pages ------------------ */
self.addEventListener('message', event => {
  const { type } = event.data || {};

  switch (type) {
    case 'PING':
      event.source.postMessage({ type: 'PONG', status: onlineStatus });
      break;

    case 'CLEAR_CACHE':
      event.waitUntil(
        (async () => {
          await caches.delete(DYNAMIC_CACHE);
          await caches.delete(CACHE_NAME);
          broadcast('CACHE_CLEARED');
        })()
      );
      break;

    default:
      console.log('[ServiceWorker] Unknown message type:', type);
  }
});
