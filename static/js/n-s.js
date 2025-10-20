class LyxNexusNotificationService {
    constructor() {
        this.socket = null;
        this.notificationPermission = Notification.permission;
        this.isInitialized = false;
        this.serviceName = 'LyxNexus-Notification-Service';
        this.isWebView = /(wv|WebView|AndroidWebView|Appilix)/i.test(navigator.userAgent);

        this.audio = new Audio('/uploads/notify.mp3');
        this.audio.preload = 'auto';
        this.audio.volume = 0.7; 

        console.log(`${this.serviceName}: Created, waiting for dependencies...`);
        this.startInitialization();
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
        this.setupEventListeners();
        this.isInitialized = true;
        console.log(`${this.serviceName}: Ready and listening for notifications`);
    }

    setupSocketConnection() {
        try {
            this.socket = io();
            this.socket.on('connect', () => console.log(`${this.serviceName}: ✅ Connected to server`));
            this.socket.on('disconnect', () => console.log(`${this.serviceName}: Disconnected from server`));

            this.socket.on('new_message', (data) => {
                console.log(`${this.serviceName}: Received new message:`, data);
                this.handleNewMessage(data);
            });

            this.socket.on('push_notification', (data) => {
                console.log(`${this.serviceName}: Received push notification:`, data);
                this.handlePushNotification(data);
            });

        } catch (error) {
            console.error(`${this.serviceName}: Socket setup failed:`, error);
            throw error;
        }
    }

    async requestPermission() {
        if (!('Notification' in window)) {
            console.warn(`${this.serviceName}: ❌ Browser doesn't support notifications`);
            return;
        }

        if (this.notificationPermission === 'default') {
            try {
                this.notificationPermission = await Notification.requestPermission();
                console.log(`${this.serviceName}: Notification permission: ${this.notificationPermission}`);
            } catch (error) {
                console.error(`${this.serviceName}: Permission request failed:`, error);
            }
        } else {
            console.log(`${this.serviceName}: Notification permission: ${this.notificationPermission}`);
        }
    }

    setupEventListeners() {
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                console.log(`${this.serviceName}: Page hidden - enabling background mode`);
            }
        });
    }

    retryInitialization() {
        console.log(`${this.serviceName}: 🔄 Retrying initialization in 2 seconds...`);
        setTimeout(() => this.startInitialization(), 2000);
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    handleNewMessage(messageData) {
        if (!this.isInitialized) {
            console.warn(`${this.serviceName}: Not initialized, cannot show message notification`);
            return;
        }

        try {
            const currentUserId = this.getCurrentUserId();
            if (messageData.user_id == currentUserId && !document.hidden) {
                console.log(`${this.serviceName}: Own message, skipping notification`);
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
                    data: {
                        type: 'message',
                        messageId: messageData.id,
                        room: messageData.room
                    }
                }
            );
        } catch (error) {
            console.error(`${this.serviceName}: Error handling new message:`, error);
        }
    }

    handlePushNotification(data) {
        if (!this.isInitialized) return;
        this.showNotification(
            data.title || '🔔 LyxNexus',
            data.message,
            {
                icon: '/uploads/favicon-1.png',
                tag: `push-${Date.now()}`,
                data: data
            }
        );
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
            const notificationOptions = {
                body: message,
                icon: options.icon || '/uploads/favicon-1.png',
                badge: '/uploads/favicon-1.png',
                tag: options.tag || 'lynxnexus-general',
                requireInteraction: options.important || false,
                data: options.data || {}
            };

            const notification = new Notification(title, notificationOptions);
            this.playSound();

            console.log(`${this.serviceName}: ✅ Notification shown: ${title}`);

            notification.onclick = () => {
                window.focus();
                notification.close();
                this.redirectFromData(options.data);
            };

            notification.onclose = () => {
                console.log(`${this.serviceName}: Notification closed: ${title}`);
            };

            setTimeout(() => notification?.close(), 7 * 60 * 60 * 1000);
            return notification;
        } catch (error) {
            console.error(`${this.serviceName}: ❌ Failed to show system notification, using fallback`, error);
            this.showInAppToast(title, message, options);
            return null;
        }
    }

    playSound() {
        try {
            this.audio.currentTime = 0;
            this.audio.play().catch(() => {
                console.warn(`${this.serviceName}: Sound play deferred until user interaction`);
            });
        } catch (e) {
            console.warn(`${this.serviceName}: Sound play failed`, e);
        }
    }

    showInAppToast(title, message, options = {}) {
        this.playSound();

        if (this.isWebView || !('Notification' in window)) {
            alert(`${title}\n\n${message}`);
            return;
        }

        const toast = document.createElement('div');
        toast.classList.add('lynx-toast');
        toast.innerHTML = `
            <div class="lynx-toast-header" style="display:flex; align-items:center;">
                <img src="${options.icon || '/uploads/favicon-1.png'}" 
                     class="lynx-toast-icon" 
                     style="width:32px; height:32px; margin-right:10px; border-radius:6px;" 
                     alt="icon">
                <span class="lynx-toast-title" style="font-weight:600;">${title}</span>
            </div>
            <div class="lynx-toast-message" style="margin-top:4px; font-size:0.875rem;">${message}</div>
            <div class="lynx-toast-actions" style="margin-top:6px; display:flex; gap:8px;"></div>
        `;

        // Optional SMS button
        if (window.current_user?.number) {
            const smsLink = document.createElement('a');
            smsLink.href = `https://api.whatsapp.com/send?phone=${window.current_user.number}&text=${encodeURIComponent(message)}`;
            smsLink.target = "_blank";
            smsLink.textContent = "Send SMS";
            smsLink.style.cssText = "color:#1DA1F2; font-size:0.8rem; text-decoration:underline; cursor:pointer;";
            toast.querySelector('.lynx-toast-actions').appendChild(smsLink);
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

        setTimeout(() => {
            toast.style.opacity = '1';
            toast.style.transform = 'translateX(0)';
        }, 50);

        toast.onclick = () => {
            this.redirectFromData(options.data);
            toast.remove();
        };

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(40px)';
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }

    redirectFromData(data) {
        if (!data) return;
        if (data.type === 'message' && window.location.pathname !== '/messages') {
            window.location.href = '/messages';
        } else if (['announcement', 'assignment', 'timetable'].includes(data.type)
            && window.location.pathname !== '/main-page') {
            window.location.href = '/main-page';
        }
    }

    getCurrentUserId() {
        if (window.currentUserId) return window.currentUserId;
        if (window.current_user && window.current_user.id) return window.current_user.id;
        if (typeof current_user !== 'undefined' && current_user.id) return current_user.id;
        const el = document.querySelector('[data-user-id]');
        if (el) return el.getAttribute('data-user-id');
        return localStorage.getItem('current_user_id') || -1;
    }

    testNotification() {
        if (!this.isInitialized) {
            console.warn(`${this.serviceName}: ❌ Not initialized yet`);
            return;
        }
        this.showNotification('Test Notification', 'This is a test notification from LyxNexus', {
            icon: '/uploads/favicon-1.png',
            tag: 'test-notification',
            data: { type: 'test' }
        });
    }

    getStatus() {
        return {
            isInitialized: this.isInitialized,
            socketConnected: this.socket?.connected || false,
            notificationPermission: this.notificationPermission,
            serviceName: this.serviceName
        };
    }
}

window.initLyxNexusNotifications = function() {
    try {
        if (window.LyxNexusNotifications) {
            console.log('LyxNexus Notification Service already initialized');
            return window.LyxNexusNotifications;
        }
        window.LyxNexusNotifications = new LyxNexusNotificationService();
        return window.LyxNexusNotifications;
    } catch (error) {
        console.error('Failed to initialize LyxNexus Notification Service:', error);
        return null;
    }
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        console.log('DOM loaded, initializing notification service...');
        setTimeout(() => window.initLyxNexusNotifications(), 500);
    });
} else {
    console.log('DOM already ready, initializing notification service...');
    setTimeout(() => window.initLyxNexusNotifications(), 500);
}
