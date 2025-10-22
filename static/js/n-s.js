class LyxNexusNotificationService {
    constructor() {
        this.socket = null;
        this.notificationPermission = Notification.permission;
        this.isInitialized = false;
        this.serviceName = 'LyxNexus-Notification-Service';

        // Detect WebView environments (Appilix, AndroidWebView, etc.)
        this.isWebView = /(wv|WebView|AndroidWebView|Appilix|Mozilla|Applekit)/i.test(navigator.userAgent);

        // Preload notification sound
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

 async startInitialization() {
    try {
        await this.delay(1000); // Wait briefly before checking dependencies

        if (typeof io === 'undefined') {
            console.warn(`${this.serviceName}: Socket.IO not loaded, retrying in 2s...`);
            this.retryInitialization();
            return;
        }

        await this.initializeService();
    } catch (error) {
        console.warn(`${this.serviceName}: Socket.IO not loaded, retrying in 2s...`);
        this.retryInitialization();
    }
}

retryInitialization() {
    setTimeout(() => this.startInitialization(), 2000); // Retry after 2 seconds
}

setupSocketConnection() {
    try {
        this.socket = io();

        this.socket.on('connect', () => {
            console.log(`[${this.serviceName}]: ✅ Connected to server`);
        });

        this.socket.on('disconnect', () => {
            console.warn(`[${this.serviceName}]: ❌ Disconnected from server`);
        });

        // Incoming direct messages
        this.socket.on('new_message', (data) => {
            this.handleNewMessage(data);
        });

        // Incoming push-style notifications (e.g. announcements)
        this.socket.on('push_notification', (data) => {
            this.handlePushNotification(data);
        });

    } catch (error) {
        console.error(`[${this.serviceName}]: Socket setup failed:`, error);
        throw error;
    }
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
            }
        });
    }

    retryInitialization() {
        setTimeout(() => this.startInitialization(), 2000);
    } // just for slow net .... and Chrome Web Apps

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms)); // for less aggressiv intervals--> pause a bit
    }

    getCurrentUserId() {
        if (window.currentUserId) return window.currentUserId;
        if (window.current_user?.id) return window.current_user.id;
        const el = document.querySelector('[data-user-id]');
        if (el) return el.getAttribute('data-user-id');
        return localStorage.getItem('current_user_id') || -1;
    }
// specified for messages allone, still updating it
async handleNewMessage(messageData) {
    const currentUserId = this.getCurrentUserId();

    // Ignore if it's your own message and you're active
    if (messageData.user_id === currentUserId && !document.hidden) return;

    const preview = messageData.content.length > 100
        ? messageData.content.substring(0, 100) + '...'
        : messageData.content;

    this.showNotification(
        `💬 ${messageData.username}`,
        preview,
        {
            icon: '/uploads/favicon-1.png',
            tag: `message-${messageData.id}`,
            data: {
                messageId: messageData.id,
                type: 'message',
                room: messageData.room
            }
        }
    );
}

async handlePushNotification(data) {
    this.showNotification(
        data.title || '🔔 LyxNexus',
        data.message,
        {
            icon: '/uploads/favicon-1.png',
            tag: `push-${Date.now()}`,
            data
        }
    );

    // Broadcast via SMS (if allowed)
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
                        body: JSON.stringify({
                            phone: u.phone,
                            message: data.message
                        })
                    });
                }
            });
        } catch (e) {
            console.error(`[${this.serviceName}]: SMS broadcast failed`, e);
        }
    }
}
                  // real deal. --> still needs a lot of updates


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

        setTimeout(() => notification?.close(), 7 * 60 * 60 * 1000); // auto-close after 7 hours
    } catch {
        this.showInAppToast(title, message, options);
    }
}

showInAppToast(title, message, options = {}) {
    this.playSound();

    if (this.isWebView || !('Notification' in window)) {
        alert(`${title}\n\n${message}`);
        return;
    }

    const toast = document.createElement('div');
    toast.innerHTML = `
        <div style="display:flex; align-items:center;">
            <img src="${options.icon || '/uploads/favicon-1.png'}" 
                 style="width:32px; height:32px; margin-right:10px; border-radius:6px;">
            <span style="font-weight:600;">${title}</span>
        </div>
        <div style="margin-top:4px; font-size:0.875rem;">${message}</div>
        <div style="margin-top:6px; display:flex; gap:8px;"></div>
    `;

    // class rep repost on groups
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
    } else if (
        ['announcement', 'assignment', 'timetable'].includes(data.type) &&
        window.location.pathname !== '/main-page'
    ) {
        window.location.href = '/main-page';
    }
}

testNotification() {
    if (!this.isInitialized) return;

    this.showNotification(
        'Test Notification',
        'This is a test notification',
        { tag: 'test' }
    );
}

getStatus() {
    return {
        isInitialized: this.isInitialized,
        socketConnected: this.socket?.connected || false,
        notificationPermission: this.notificationPermission
    };
}

// Register service globally
    if (LyxNexusNotifications) return window.LyxNexusNotifications;
window.initLykNexusNotifications = function () {
    if (window.LykNexusNotifications) return;

    window.LykNexusNotifications = new LyxNexusNotificationService();
    return window.LykNexusNotifications;
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        setTimeout(() => window.initLykNexusNotifications(), 500);
    });
} else {
    setTimeout(() => window.initLykNexusNotifications(), 500);
}