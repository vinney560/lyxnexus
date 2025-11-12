class LyxNexusNotificationService {
    constructor() {
        this.socket = null;
        this.notificationPermission = Notification.permission;
        this.isInitialized = false;
        this.serviceName = 'LyxNexus-Notification-Service';
        this.isWebView = /(wv|WebView|AndroidWebView|Appilix|AppleWebKit)(?!.*Safari)/i.test(navigator.userAgent);
        this.pendingNotifications = [];
        this.isOnline = navigator.onLine;

        this.audio = new Audio('/uploads/notify.mp3');
        this.audio.preload = 'auto';
        this.audio.volume = 0.7;

        console.log(`${this.serviceName}: Created, waiting for dependencies...`);
        this.startInitialization();
        this.setupConnectivityListeners();
    }

    async startInitialization() {
        try {
            await this.delay(1000);
            if (typeof io === 'undefined') {
                console.warn(`${this.serviceName}: Socket.IO not loaded, will retry...`);
                this.retryInitialization();
                return;
            }
            await this.initializeService();
        } catch (error) {
            console.error(`${this.serviceName}: Startup failed:`, error);
            this.retryInitialization();
        }
    }

    async initializeService() {
        console.log(`${this.serviceName}: Starting initialization...`);
        this.setupSocketConnection();
        await this.requestPermission();
        await this.subscribeForPush();
        this.setupEventListeners();
        this.isInitialized = true;
        
        // Process any pending notifications that were stored while offline
        await this.processPendingNotifications();
        
        console.log(`${this.serviceName}: Ready and listening for notifications`);
    }

    setupConnectivityListeners() {
        window.addEventListener('online', () => {
            console.log(`${this.serviceName}: Online - processing pending notifications`);
            this.isOnline = true;
            this.processPendingNotifications();
            this.reconnectSocket();
        });

        window.addEventListener('offline', () => {
            console.log(`${this.serviceName}: Offline - storing notifications locally`);
            this.isOnline = false;
        });
    }

    setupSocketConnection() {
        try {
            let baseUrl;

            if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
                baseUrl = "https://lyxnexus.onrender.com";
            } else {
                baseUrl = window.location.origin;
            }

            baseUrl = baseUrl.replace(/\/+$/, '');

            this.socket = io(baseUrl, {
                path: "/socket.io",
                transports: ["websocket", "polling"],
                reconnection: true,
                reconnectionAttempts: Infinity,
                reconnectionDelay: 1000,
                reconnectionDelayMax: 10000
            });

            this.socket.on('connect', () => {
                console.log(`${this.serviceName}: ✅ Connected to server`);
                // Sync any missed notifications when reconnecting
                this.syncMissedNotifications();
            });
            
            this.socket.on('disconnect', () => console.log(`${this.serviceName}: ❌ Disconnected from server`));

            this.socket.on('new_message', (data) => this.handleNewMessage(data));
            this.socket.on('push_notification', (data) => this.handlePushNotification(data));

        } catch (error) {
            console.error(`${this.serviceName}: Socket setup failed:`, error);
            throw error;
        }
    }

    reconnectSocket() {
        if (this.socket && !this.socket.connected) {
            this.socket.connect();
        }
    }

    async syncMissedNotifications() {
        try {
            // Request missed notifications from server
            const lastSeen = localStorage.getItem('last_notification_seen') || Date.now() - (60 * 60 * 1000); // 1 hour ago
            this.socket.emit('sync_notifications', { lastSeen, userId: this.getCurrentUserId() });
        } catch (error) {
            console.error(`${this.serviceName}: Failed to sync missed notifications:`, error);
        }
    }

    async storeNotificationOffline(notificationData) {
        try {
            const stored = await this.getStoredNotifications();
            const notification = {
                ...notificationData,
                id: `offline_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                timestamp: Date.now(),
                storedOffline: true
            };
            
            stored.push(notification);
            
            // Keep only last 50 notifications to prevent storage overflow
            if (stored.length > 50) {
                stored.splice(0, stored.length - 50);
            }
            
            localStorage.setItem('pending_notifications', JSON.stringify(stored));
            this.pendingNotifications = stored;
            
            console.log(`${this.serviceName}: Stored notification offline (total: ${stored.length})`);
        } catch (error) {
            console.error(`${this.serviceName}: Failed to store notification offline:`, error);
        }
    }

    async getStoredNotifications() {
        try {
            const stored = localStorage.getItem('pending_notifications');
            return stored ? JSON.parse(stored) : [];
        } catch {
            return [];
        }
    }

    async processPendingNotifications() {
        if (!this.isOnline) return;

        const pending = await this.getStoredNotifications();
        if (pending.length === 0) return;

        console.log(`${this.serviceName}: Processing ${pending.length} pending notifications`);

        // Sort by timestamp (oldest first)
        pending.sort((a, b) => a.timestamp - b.timestamp);

        for (const notification of pending) {
            try {
                // Add small delay between notifications for better UX
                await this.delay(500);
                
                if (notification.type === 'message') {
                    await this.handleNewMessage(notification.data || notification);
                } else {
                    await this.handlePushNotification(notification.data || notification);
                }
            } catch (error) {
                console.error(`${this.serviceName}: Failed to process pending notification:`, error);
            }
        }

        // Clear processed notifications
        localStorage.removeItem('pending_notifications');
        this.pendingNotifications = [];
        
        // Update last seen timestamp
        localStorage.setItem('last_notification_seen', Date.now());
    }

    async requestPermission() {
        if (!('Notification' in window)) return;

        if (this.notificationPermission === 'default') {
            try {
                this.notificationPermission = await Notification.requestPermission();
            } catch (error) {
                console.error(`${this.serviceName}: Permission denied:`, error);
            }
        }
    }

    setupEventListeners() {
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                console.log(`${this.serviceName}: Page hidden - background mode enabled!`);
            } else {
                // Page became visible, check for pending notifications
                this.processPendingNotifications();
            }
        });
    }

    retryInitialization() {
        setTimeout(() => this.startInitialization(), 2000);
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    getCurrentUserId() {
        if (window.currentUserId) return window.currentUserId;
        if (window.current_user?.id) return window.current_user.id;
        const el = document.querySelector('[data-user-id]');
        if (el) return el.getAttribute('data-user-id');
        return localStorage.getItem('current_user_id') || -1;
    }

    async handleNewMessage(messageData) {
        const currentUserId = this.getCurrentUserId();
        
        // Don't show user's own messages and if page is visible
        if (messageData.user_id == currentUserId && !document.hidden) return;

        // If offline, store notification for later
        if (!this.isOnline) {
            await this.storeNotificationOffline({
                type: 'message',
                data: messageData,
                title: `💬 ${messageData.username}`,
                message: messageData.content.length > 100 
                    ? messageData.content.substring(0, 100) + '...' 
                    : messageData.content
            });
            return;
        }

        this.showNotification(
            `💬 ${messageData.username}`,
            messageData.content.length > 100
                ? messageData.content.substring(0, 100) + '...'
                : messageData.content,
            {
                icon: '/uploads/favicon-1.png',
                tag: `message-${messageData.id}`,
                data: { type: 'message', messageId: messageData.id, room: messageData.room }
            }
        );
    }

    async handlePushNotification(data) {
        // If offline, store notification for later
        if (!this.isOnline) {
            await this.storeNotificationOffline({
                type: 'push',
                data: data,
                title: data.title || '🔔 LyxNexus',
                message: data.message
            });
            return;
        }

        this.showNotification(
            data.title || '🔔 LyxNexus',
            data.message,
            { icon: '/uploads/favicon-1.png', tag: `push-${Date.now()}`, data }
        );

        if (data.broadcast) {
            try {
                const res = await fetch('/api/users-sms/');
                const users = await res.json();
                const currentUserId = this.getCurrentUserId();
                users.forEach(u => {
                    if (u.id != currentUserId && u.phone) {
                        fetch('/api/send_sms', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ phone: u.phone, message: data.message })
                        });
                    }
                });
            } catch (e) {
                console.error(`${this.serviceName}: Failed to broadcast SMS`, e);
            }
        }
    }

    showNotification(title, message, options = {}) {
        if (!('Notification' in window) || this.isWebView) {
            this.showInAppToast(title, message, options);
            return;
        }

        if (this.notificationPermission !== 'granted') {
            this.showInAppToast(title, message, options);
            return;
        }

        try {
            const notification = new Notification(title, {
                body: message,
                icon: options.icon || '/uploads/favicon-1.png',
                badge: '/uploads/favicon-1.png',
                tag: options.tag || 'lynxnexus-general',
                data: options.data || {}
            });

            this.playSound();

            notification.onclick = () => {
                window.focus();
                notification.close();
                this.redirectFromData(options.data);
            };

            setTimeout(() => notification?.close(), 7 * 60 * 60 * 1000);
        } catch {
            this.showInAppToast(title, message, options);
        }
    }

    playSound() {
        try {
            this.audio.currentTime = 0;
            this.audio.play().catch(() => {});
        } catch {}
    }

    showInAppToast(title, message, options = {}) {
        this.playSound();

        if (this.isWebView || !('Notification' in window)) {
            alert(`${title}\n\n${message}`);
            return;
        }

        const toast = document.createElement('div');
        toast.className = 'lynx-toast';
        toast.innerHTML = `
            <div style="display:flex; align-items:center;">
                <img src="${options.icon || '/uploads/favicon-1.png'}" 
                     style="width:32px; height:32px; margin-right:10px; border-radius:6px;">
                <span style="font-weight:600;">${title}</span>
            </div>
            <div style="margin-top:4px; font-size:0.875rem;">${message}</div>
            <div style="margin-top:6px; display:flex; gap:8px;"></div>
        `;

        if (window.current_user?.number) {
            const smsLink = document.createElement('a');
            smsLink.href = `https://api.whatsapp.com/send?phone=${window.current_user.number}&text=${encodeURIComponent(message)}`;
            smsLink.target = "_blank";
            smsLink.textContent = "Send SMS";
            smsLink.style.cssText = "color:#1DA1F2; font-size:0.8rem; text-decoration:underline; cursor:pointer;";
            toast.querySelector('div:last-child').appendChild(smsLink);
        }

        const offset = 20 + document.querySelectorAll('.lynx-toast').length * 70;
        Object.assign(toast.style, {
            position: 'fixed',
            bottom: `${offset}px`,
            right: '20px',
            background: 'rgba(25,25,25,0.95)',
            color: '#fff',
            padding: '10px 14px',
            borderRadius: '10px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
            zIndex: 999999,
            width: '85%',
            maxWidth: '300px',
            fontFamily: 'system-ui, sans-serif',
            cursor: 'pointer',
            transform: 'translateX(40px)',
            opacity: '0',
            transition: 'transform 0.3s ease-out, opacity 0.3s ease-out'
        });

        setTimeout(() => { toast.style.opacity = '1'; toast.style.transform = 'translateX(0)'; }, 50);
        toast.onclick = () => { this.redirectFromData(options.data); toast.remove(); };
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(40px)';
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }

    redirectFromData(data) {
        if (!data) return;
        if (data.type === 'message' && window.location.pathname !== '/messages') window.location.href = '/messages';
        else if (['announcement','assignment','timetable'].includes(data.type) && window.location.pathname !== '/main-page') window.location.href = '/main-page';
    }

    async subscribeForPush() {
        if (!("serviceWorker" in navigator)) {
            console.warn(`${this.serviceName}: Service Worker not supported.`);
            return;
        }

        const registration = await navigator.serviceWorker.ready;

        const publicVapidKey = "BEk4C5_aQbjOMkvGYk4OFZMyMAInUdVP6oAFs9kAd7Gx3iog2UF4ZLwdQ8GmB0-i61FANGD6D0TCHsFYVOA45OQ";
        const convertedKey = this.urlBase64ToUint8Array(publicVapidKey);

        try {
            const subscription = await registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: convertedKey
            });

            console.log(`${this.serviceName}: Push subscription successful.`);

            const subscriptionData = subscription.toJSON();

            const userId = window.currentUserId || await new Promise(resolve => {
                const interval = setInterval(() => {
                    if (window.currentUserId) { clearInterval(interval); resolve(window.currentUserId); }
                }, 500);
            });

            subscriptionData.user_id = userId;

            console.log("📩 Sending subscription to backend:", subscriptionData);

            await fetch("/subscribe", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(subscriptionData)
            });

            console.log(`${this.serviceName}: ✅ Push notifications subscribed.`);
        } catch (err) {
            console.error(`${this.serviceName}: Failed to subscribe for push`, err);
        }
    }

    urlBase64ToUint8Array(base64String) {
        const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
        const base64 = (base64String + padding)
            .replace(/\-/g, "+")
            .replace(/_/g, "/");
        const rawData = atob(base64);
        return Uint8Array.from([...rawData].map((char) => char.charCodeAt(0)));
    }

    testNotification() {
        if (!this.isInitialized) return;
        this.showNotification('Test Notification', 'This is a test notification', { tag:'test' });
    }

    getStatus() {
        return { 
            isInitialized: this.isInitialized, 
            socketConnected: this.socket?.connected || false, 
            notificationPermission: this.notificationPermission,
            isOnline: this.isOnline,
            pendingNotifications: this.pendingNotifications.length
        };
    }

    // Method to manually clear pending notifications
    clearPendingNotifications() {
        localStorage.removeItem('pending_notifications');
        this.pendingNotifications = [];
        console.log(`${this.serviceName}: Cleared all pending notifications`);
    }
}

window.initLyxNexusNotifications = function() {
    if (window.LyxNexusNotifications) return window.LyxNexusNotifications;
    window.LyxNexusNotifications = new LyxNexusNotificationService();
    return window.LyxNexusNotifications;
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => setTimeout(() => window.initLyxNexusNotifications(), 500));
} else {
    setTimeout(() => window.initLyxNexusNotifications(), 500);
}