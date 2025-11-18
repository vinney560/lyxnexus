// firebase-messaging-sw.js
importScripts('https://www.gstatic.com/firebasejs/12.6.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/12.6.0/firebase-messaging-compat.js');

// Initialize Firebase
firebase.initializeApp({
    apiKey: "AIzaSyDiySIsbCQ-uNEuqu3ZT1wFUkWkdwD7cbw",
    authDomain: "lyxnexus.onrender.com",
    projectId: "lyxnexus",
    storageBucket: "lyxnexus.firebasestorage.app",
    messagingSenderId: "130771054418",
    appId: "1:130771054418:web:e2c2371cc2844a24e8148b"
});

const messaging = firebase.messaging();

// Handle background messages
messaging.onBackgroundMessage((payload) => {
    console.log('Received background message:', payload);

    const notificationTitle = payload.notification?.title || 'Lyx Nexus';
    const notificationOptions = {
        body: payload.notification?.body || 'You have a new message',
        icon: '/uploads/favicon.png',
        data: payload.data || {}
    };

    self.registration.showNotification(notificationTitle, notificationOptions);
});

// Handle notification click
self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    
    event.waitUntil(
        clients.matchAll({ type: 'window' }).then((clientList) => {
            for (const client of clientList) {
                if (client.url.includes('lyxnexus.onrender.com') && 'focus' in client) {
                    return client.focus();
                }
            }
            if (clients.openWindow) {
                return clients.openWindow('https://lyxnexus.onrender.com');
            }
        })
    );
});