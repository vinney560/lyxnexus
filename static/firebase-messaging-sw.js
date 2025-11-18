// firebase-messaging-sw.js - Save this file in the same directory as your HTML
importScripts('https://www.gstatic.com/firebasejs/12.6.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/12.6.0/firebase-messaging-compat.js');

// Initialize Firebase
firebase.initializeApp({
    apiKey: "AIzaSyBsp_fIfnXefjjFBgxX7yl6QWQzFM5HXnY",
    authDomain: "lyxnexus.onrender.com",
    projectId: "lyx-nexus-bcmzqb",
    storageBucket: "lyx-nexus-bcmzqb.firebasestorage.app",
    messagingSenderId: "954068330281",
    appId: "1:954068330281:web:032ae6946a930abc92f938"
});

const messaging = firebase.messaging();

// Handle background messages
messaging.onBackgroundMessage((payload) => {
    console.log('Received background message:', payload);

    const notificationTitle = payload.notification?.title || 'Lyx Nexus';
    const notificationOptions = {
        body: payload.notification?.body || 'You have a new message',
        icon: 'https://lyxnexus.onrender.com/icon.png', // Use absolute URL or remove
        data: payload.data || {}
    };

    self.registration.showNotification(notificationTitle, notificationOptions);
});

// Handle notification click
self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    
    event.waitUntil(
        clients.matchAll({ type: 'window' }).then((clientList) => {
            // Focus existing window or open new one
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