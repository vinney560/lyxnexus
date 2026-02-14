const CACHE_NAME = 'lyxnexus-static-v4';
const DYNAMIC_CACHE = 'lyxnexus-dynamic-v3';
const NOTIFICATION_CACHE = 'lyxnexus-notifications-v1';
const OFFLINE_URL = '/offline.html';

const STATIC_ASSETS = [
  '/',
  '/login',
  '/main-page',
  '/offline.html',
  '/uploads/favicon-1.png',
  '/uploads/notify.mp3',
  '/static/css/tailwind.min.css',
  '/static/css/tailwind.all.css',
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

/* ------------------ Notification Storage ------------------ */
async function storeNotificationForOffline(notificationData) {
  try {
    const cache = await caches.open(NOTIFICATION_CACHE);
    const notificationId = `notification_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const notification = {
      ...notificationData,
      id: notificationId,
      timestamp: Date.now(),
      storedOffline: true
    };

    const response = new Response(JSON.stringify(notification), {
      headers: { 'Content-Type': 'application/json' }
    });

    await cache.put(`/notification/${notificationId}`, response);
    console.log('[ServiceWorker] Stored notification for offline delivery:', notificationId);
    
    return notificationId;
  } catch (error) {
    console.error('[ServiceWorker] Failed to store notification:', error);
  }
}

async function getStoredNotifications() {
  try {
    const cache = await caches.open(NOTIFICATION_CACHE);
    const keys = await cache.keys();
    const notifications = [];

    for (const request of keys) {
      if (request.url.includes('/notification/')) {
        const response = await cache.match(request);
        if (response) {
          const notification = await response.json();
          notifications.push(notification);
        }
      }
    }

    // Sort by timestamp (oldest first)
    return notifications.sort((a, b) => a.timestamp - b.timestamp);
  } catch (error) {
    console.error('[ServiceWorker] Failed to get stored notifications:', error);
    return [];
  }
}

async function clearStoredNotification(notificationId) {
  try {
    const cache = await caches.open(NOTIFICATION_CACHE);
    await cache.delete(`/notification/${notificationId}`);
  } catch (error) {
    console.error('[ServiceWorker] Failed to clear notification:', error);
  }
}

async function clearAllStoredNotifications() {
  try {
    const cache = await caches.open(NOTIFICATION_CACHE);
    const keys = await cache.keys();
    
    for (const request of keys) {
      if (request.url.includes('/notification/')) {
        await cache.delete(request);
      }
    }
    console.log('[ServiceWorker] Cleared all stored notifications');
  } catch (error) {
    console.error('[ServiceWorker] Failed to clear all notifications:', error);
  }
}

async function deliverStoredNotifications() {
  if (!onlineStatus) return;

  const notifications = await getStoredNotifications();
  if (notifications.length === 0) return;

  console.log(`[ServiceWorker] Delivering ${notifications.length} stored notifications`);

  for (const notification of notifications) {
    try {
      // Show the notification
      await self.registration.showNotification(
        notification.title || '🔔 LyxNexus',
        {
          body: notification.body || notification.message,
          icon: notification.icon || '/uploads/favicon-1.png',
          badge: '/uploads/favicon-1.png',
          data: notification.data || {},
          tag: notification.tag || `stored-${notification.id}`
        }
      );

      // Broadcast to clients
      await broadcast('STORED_NOTIFICATION_DELIVERED', {
        title: notification.title,
        body: notification.body || notification.message,
        data: notification.data
      });

      // Remove from storage after successful delivery
      await clearStoredNotification(notification.id);
      
      // Small delay between notifications
      await new Promise(resolve => setTimeout(resolve, 1000));
      
    } catch (error) {
      console.error('[ServiceWorker] Failed to deliver stored notification:', error);
    }
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
      if (![CACHE_NAME, DYNAMIC_CACHE, NOTIFICATION_CACHE].includes(key)) {
        await caches.delete(key);
      }
    }

    // Refresh open clients after activation
    const clients = await self.clients.matchAll({ type: 'window' });
    for (const client of clients) {
      client.navigate(client.url);
    }
    
    // Deliver any stored notifications that accumulated during update
    await deliverStoredNotifications();
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
      
      // If coming online, deliver stored notifications
      if (status) {
        deliverStoredNotifications();
      }
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
    (async () => {
      // If offline, store the notification for later delivery
      if (!onlineStatus) {
        console.log('[ServiceWorker] Offline - storing push notification');
        await storeNotificationForOffline({
          title,
          body,
          icon,
          tag,
          data: { ...data, url: clickUrl }
        });
        return;
      }

      // If online, show immediately
      await self.registration.showNotification(title, {
        body,
        icon,
        badge: icon,
        data: { ...data, url: clickUrl },
        tag
      });

      broadcast('PUSH_RECEIVED', { title, body });
    })()
  );
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

/* ------------------ Background Sync for Notifications ------------------ */
self.addEventListener('sync', event => {
  if (event.tag === 'notification-sync') {
    console.log('[ServiceWorker] Background sync for notifications');
    event.waitUntil(deliverStoredNotifications());
  }
});

/* ------------------ Messaging From Client Pages ------------------ */
self.addEventListener('message', event => {
  const { type, data } = event.data || {};

  switch (type) {
    case 'PING':
      event.source.postMessage({ type: 'PONG', status: onlineStatus });
      break;

    case 'CLEAR_CACHE':
      event.waitUntil(
        (async () => {
          await caches.delete(DYNAMIC_CACHE);
          await caches.delete(CACHE_NAME);
          await clearAllStoredNotifications();
          broadcast('CACHE_CLEARED');
        })()
      );
      break;

    case 'GET_PENDING_NOTIFICATIONS':
      event.waitUntil(
        (async () => {
          const notifications = await getStoredNotifications();
          event.source.postMessage({ 
            type: 'PENDING_NOTIFICATIONS', 
            data: notifications 
          });
        })()
      );
      break;

    case 'STORE_NOTIFICATION_OFFLINE':
      event.waitUntil(
        (async () => {
          await storeNotificationForOffline(data);
          event.source.postMessage({ 
            type: 'NOTIFICATION_STORED' 
          });
        })()
      );
      break;

    case 'DELIVER_STORED_NOTIFICATIONS':
      event.waitUntil(deliverStoredNotifications());
      break;

    default:
      console.log('[ServiceWorker] Unknown message type:', type);
  }
});