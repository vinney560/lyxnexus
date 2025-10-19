class LyxNexusNotificationService {
    constructor() {
        this.socket = null;
        this.notificationPermission = Notification.permission;
        this.isInitialized = false;
        this.serviceName = 'LyxNexus-Notification-Service';
        
        console.log(`${this.serviceName}: Created, waiting for dependencies...`);
        
        this.startInitialization();
    }

    async startInitialization() {
        try {
            // Wait  Socket.IO to load
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
            
            this.socket.on('connect', () => {
                console.log(`${this.serviceName}: ✅ Connected to server`);
            });
            
            this.socket.on('disconnect', () => {
                console.log(`${this.serviceName}: Disconnected from server`);
            });
            
            // Listen for new messages
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
        setTimeout(() => {
            this.startInitialization();
        }, 2000);
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

            console.log(`${this.serviceName}: Showing notification for message from ${messageData.username}`);
            
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
        if (this.notificationPermission !== 'granted') {
            console.warn(`${this.serviceName}: ❌ Notifications not ALLOWED!`);
            return null;
        }

        try {
            const notificationOptions = {
                icon: options.icon || '/uploads/favicon-1.png',
                badge: '/uploads/favicon-1.png',
                tag: options.tag || 'lynxnexus-general',
                requireInteraction: options.important || false,
                data: options.data || {}
            };

            const notification = new Notification(title, notificationOptions);
            
            console.log(`${this.serviceName}: ✅ Notification shown: ${title}`);
            
            notification.onclick = () => {
                console.log(`${this.serviceName}: Notification clicked`);
                window.focus();
                notification.close();
                
                if (options.data?.type === 'message' && window.location.pathname !== '/messages') {
                    window.location.href = '/messages';
                }
                else if (options.data?.type === 'announcement' && window.location.pathname !== '/main-page') {
                    window.location.href = '/main-page';
                }
                else if (options.data?.type === 'assignment' && window.location.pathname !== '/main-page') {
                    window.location.href = '/main-page';
                }
                else if (options.data?.type === 'timetable' && window.location.pathname !== '/main-page') {
                    window.location.href = '/main-page';
                }
            };

            notification.onclose = () => {
                console.log(`${this.serviceName}: Notification closed: ${title}`);
            };

            // close after shown --> 7 hrs
            setTimeout(() => {
                if (notification) {
                    notification.close();
                }
            }, 7 * 60 * 60 * 1000); // if 1000 --> 1 secs and 2hrs --> 7* 60 * 60 * 1000

            return notification;
            
        } catch (error) {
            console.error(`${this.serviceName}: ❌ Failed to show notification:`, error);
            return null;
        }
    }

    getCurrentUserId() {
        if (window.currentUserId) return window.currentUserId;
        if (window.current_user && window.current_user.id) return window.current_user.id;
        if (typeof current_user !== 'undefined' && current_user.id) return current_user.id;
        
        const userIdElement = document.querySelector('[data-user-id]');
        if (userIdElement) return userIdElement.getAttribute('data-user-id');
        
        return localStorage.getItem('current_user_id') || -1;
    }

    // Testing
    testNotification() {
        if (!this.isInitialized) {
            console.warn(`${this.serviceName}: ❌ Not initialized yet - current status:`, {
                isInitialized: this.isInitialized,
                socketReady: !!this.socket,
                permission: this.notificationPermission
            });
            return;
        }

        console.log(`${this.serviceName}: Testing notification...`);
        
        this.showNotification(
            'Test Notification',
            'This is a test notification from LyxNexus',
            {
                icon: '/uploads/favicon-1.png',
                tag: 'test-notification',
                data: { type: 'test' }
            }
        );
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

// Auto cialze when page loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        console.log('DOM loaded, initializing notification service...');
        setTimeout(() => {
            window.initLyxNexusNotifications();
        }, 500);
    });
} else {
    console.log('DOM already ready, initializing notification service...');
    setTimeout(() => {
        window.initLyxNexusNotifications();
    }, 500);
}