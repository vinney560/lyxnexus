from flask import Flask, render_template_string, request, jsonify
import os
import time
import json
import threading
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import base64
from io import BytesIO
from PIL import Image
import qrcode

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global variables
whatsapp_status = "Not Connected"
qr_code_base64 = None
driver = None
bot_thread = None
MESSAGES_QUEUE = []
SESSION_FILE = "whatsapp_session.json"

# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>WhatsApp Bot</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: Arial, sans-serif; }
        body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; color: white; margin-bottom: 30px; padding: 20px; }
        .header h1 { font-size: 2.5rem; margin-bottom: 10px; }
        .header p { font-size: 1.2rem; opacity: 0.9; }
        
        .dashboard { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px; }
        @media (max-width: 768px) { .dashboard { grid-template-columns: 1fr; } }
        
        .card { background: white; border-radius: 15px; padding: 25px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }
        .card h2 { color: #333; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid #667eea; }
        
        .status-box { text-align: center; }
        .status-indicator { 
            display: inline-block; 
            width: 20px; height: 20px; 
            border-radius: 50%; 
            margin-right: 10px;
            background-color: #ff4757;
            box-shadow: 0 0 10px #ff4757;
        }
        .status-indicator.connected { background-color: #2ed573; box-shadow: 0 0 10px #2ed573; }
        .status-indicator.scanning { background-color: #ffa502; box-shadow: 0 0 10px #ffa502; animation: pulse 1.5s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        
        #statusText { font-size: 1.5rem; font-weight: bold; color: #333; }
        
        .qr-container { text-align: center; }
        #qrImage { max-width: 300px; border: 5px solid #f1f2f6; border-radius: 10px; margin: 20px auto; }
        
        .btn { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; border: none; padding: 12px 30px;
            border-radius: 25px; font-size: 1rem; cursor: pointer;
            margin: 10px 5px; transition: transform 0.3s, box-shadow 0.3s;
            text-decoration: none; display: inline-block;
        }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(0,0,0,0.3); }
        .btn-danger { background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); }
        .btn-success { background: linear-gradient(135deg, #2ed573 0%, #1e90ff 100%); }
        
        .message-form input, .message-form textarea {
            width: 100%; padding: 12px; margin: 8px 0 20px;
            border: 2px solid #ddd; border-radius: 8px;
            font-size: 1rem; transition: border 0.3s;
        }
        .message-form input:focus, .message-form textarea:focus {
            border-color: #667eea; outline: none;
        }
        
        .message-log { max-height: 300px; overflow-y: auto; }
        .message-item { 
            padding: 10px 15px; margin: 8px 0; 
            background: #f8f9fa; border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        .message-item.success { border-left-color: #2ed573; }
        .message-item.error { border-left-color: #ff6b6b; }
        .message-item.pending { border-left-color: #ffa502; }
        
        .queue-list { list-style: none; }
        .queue-item { 
            padding: 12px; margin: 8px 0; 
            background: #f8f9fa; border-radius: 8px;
            display: flex; justify-content: space-between;
            align-items: center;
        }
        
        .notification { 
            position: fixed; top: 20px; right: 20px;
            padding: 15px 25px; border-radius: 8px;
            color: white; font-weight: bold;
            display: none; z-index: 1000;
        }
        .notification.success { background: #2ed573; display: block; }
        .notification.error { background: #ff6b6b; display: block; }
    </style>
    <script>
        let eventSource;
        
        function updateStatus(status, qrCode = null) {
            const statusEl = document.getElementById('statusText');
            const indicator = document.querySelector('.status-indicator');
            const qrImg = document.getElementById('qrImage');
            
            statusEl.textContent = status;
            indicator.className = 'status-indicator';
            
            if (status.includes('Connected')) {
                indicator.classList.add('connected');
                if (qrImg) qrImg.style.display = 'none';
            } else if (status.includes('Scan')) {
                indicator.classList.add('scanning');
                if (qrCode && qrImg) {
                    qrImg.src = qrCode;
                    qrImg.style.display = 'block';
                }
            }
            
            showNotification(status, 'success');
        }
        
        function showNotification(message, type = 'success') {
            const notification = document.createElement('div');
            notification.className = `notification ${type}`;
            notification.textContent = message;
            document.body.appendChild(notification);
            
            setTimeout(() => {
                notification.remove();
            }, 3000);
        }
        
        function connectWhatsApp() {
            fetch('/start_bot', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        startEventStream();
                    } else {
                        showNotification('Failed to start bot: ' + data.error, 'error');
                    }
                });
        }
        
        function disconnectWhatsApp() {
            fetch('/stop_bot', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        updateStatus('Disconnected');
                        if (eventSource) eventSource.close();
                        showNotification('Bot disconnected');
                    }
                });
        }
        
        function sendMessage() {
            const phone = document.getElementById('phone').value;
            const message = document.getElementById('message').value;
            
            fetch('/send_message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ phone: phone, message: message })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('Message queued successfully!');
                    document.getElementById('phone').value = '';
                    document.getElementById('message').value = '';
                    loadQueue();
                } else {
                    showNotification('Error: ' + data.error, 'error');
                }
            });
        }
        
        function loadQueue() {
            fetch('/get_queue')
                .then(response => response.json())
                .then(data => {
                    const queueList = document.getElementById('queueList');
                    queueList.innerHTML = '';
                    
                    data.queue.forEach((item, index) => {
                        const li = document.createElement('li');
                        li.className = 'queue-item';
                        li.innerHTML = `
                            <div>
                                <strong>${item.phone}</strong><br>
                                <small>${item.message.substring(0, 50)}${item.message.length > 50 ? '...' : ''}</small>
                            </div>
                            <button class="btn btn-danger" onclick="removeFromQueue(${index})">Remove</button>
                        `;
                        queueList.appendChild(li);
                    });
                });
        }
        
        function removeFromQueue(index) {
            fetch('/remove_from_queue', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ index: index })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    loadQueue();
                    showNotification('Message removed from queue');
                }
            });
        }
        
        function startEventStream() {
            if (eventSource) eventSource.close();
            
            eventSource = new EventSource('/events');
            eventSource.onmessage = function(event) {
                const data = JSON.parse(event.data);
                
                if (data.type === 'status') {
                    updateStatus(data.message, data.qr_code);
                } else if (data.type === 'message_sent') {
                    showNotification(`Message sent to ${data.phone}`);
                    loadQueue();
                } else if (data.type === 'error') {
                    showNotification(data.message, 'error');
                } else if (data.type === 'connected') {
                    updateStatus('Connected to WhatsApp!');
                    showNotification('Successfully connected to WhatsApp!');
                }
            };
            
            eventSource.onerror = function() {
                console.log('EventSource error');
                setTimeout(() => startEventStream(), 5000);
            };
        }
        
        // Auto-start event stream on page load
        document.addEventListener('DOMContentLoaded', function() {
            startEventStream();
            loadQueue();
            setInterval(loadQueue, 5000);
        });
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 WhatsApp Bot Dashboard</h1>
            <p>Send WhatsApp messages directly from your browser</p>
        </div>
        
        <div class="dashboard">
            <!-- Status Card -->
            <div class="card status-box">
                <h2>Connection Status</h2>
                <div class="status-indicator"></div>
                <div id="statusText">Loading...</div>
                <div style="margin-top: 20px;">
                    <button class="btn" onclick="connectWhatsApp()">Connect WhatsApp</button>
                    <button class="btn btn-danger" onclick="disconnectWhatsApp()">Disconnect</button>
                </div>
                <div id="qrContainer" class="qr-container">
                    <img id="qrImage" alt="QR Code" style="display: none;">
                </div>
            </div>
            
            <!-- Send Message Card -->
            <div class="card">
                <h2>Send Message</h2>
                <div class="message-form">
                    <input type="text" id="phone" placeholder="Phone number (e.g., +254740694312)" required>
                    <textarea id="message" placeholder="Your message..." rows="4" required></textarea>
                    <button class="btn btn-success" onclick="sendMessage()">Send Message</button>
                </div>
            </div>
            
            <!-- Queue Card -->
            <div class="card">
                <h2>Message Queue ({{ queue_length }})</h2>
                <ul id="queueList" class="queue-list"></ul>
            </div>
            
            <!-- Log Card -->
            <div class="card">
                <h2>Recent Activity</h2>
                <div class="message-log" id="messageLog">
                    <!-- Messages will appear here via SSE -->
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

class WhatsAppBot:
    def __init__(self):
        self.driver = None
        self.connected = False
        
    def init_driver(self):
        """Initialize Chrome driver for WSL"""
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        
        # For WSL, we need to use Chrome installed in Windows
        chrome_options.binary_location = '/mnt/c/Program Files/Google/Chrome/Application/chrome.exe'
        
        # Set Chrome driver path for WSL
        driver_path = '/usr/bin/chromedriver'
        
        try:
            self.driver = webdriver.Chrome(executable_path=driver_path, options=chrome_options)
            logger.info("Chrome driver initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize driver: {e}")
            return False
    
    def login_to_whatsapp(self):
        """Login to WhatsApp Web and return QR code"""
        try:
            if not self.driver:
                if not self.init_driver():
                    return None
            
            self.driver.get('https://web.whatsapp.com')
            time.sleep(5)  # Wait for page to load
            
            # Wait for QR code to appear
            wait = WebDriverWait(self.driver, 30)
            qr_element = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "canvas[aria-label='Scan me!']"))
            )
            
            # Take screenshot of QR code
            qr_element.screenshot('qr_code.png')
            
            # Convert QR code to base64 for web display
            with open('qr_code.png', 'rb') as f:
                qr_base64 = base64.b64encode(f.read()).decode('utf-8')
            
            return f"data:image/png;base64,{qr_base64}"
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            return None
    
    def wait_for_login(self):
        """Wait for user to scan QR code"""
        try:
            wait = WebDriverWait(self.driver, 120)  # Wait 2 minutes for login
            wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='chat-list']"))
            )
            self.connected = True
            logger.info("Successfully connected to WhatsApp")
            return True
        except TimeoutException:
            logger.error("Login timeout")
            return False
    
    def send_message(self, phone_number, message):
        """Send a message to a phone number"""
        try:
            # Open chat with phone number
            self.driver.get(f'https://web.whatsapp.com/send?phone={phone_number}&text={message}')
            time.sleep(5)
            
            # Wait for send button and click
            wait = WebDriverWait(self.driver, 10)
            send_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='send']"))
            )
            send_button.click()
            
            time.sleep(2)  # Wait for message to send
            logger.info(f"Message sent to {phone_number}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message to {phone_number}: {e}")
            return False
    
    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            self.connected = False
            logger.info("Browser closed")

# Global bot instance
bot = WhatsAppBot()

@app.route('/')
def index():
    """Main dashboard"""
    return render_template_string(HTML_TEMPLATE, queue_length=len(MESSAGES_QUEUE))

@app.route('/start_bot', methods=['POST'])
def start_bot():
    """Start the WhatsApp bot"""
    global bot_thread
    
    if bot_thread and bot_thread.is_alive():
        return jsonify({'success': False, 'error': 'Bot already running'})
    
    def run_bot():
        try:
            # Generate QR code
            qr_code = bot.login_to_whatsapp()
            if qr_code:
                send_event('status', 'Scan QR code with your phone', qr_code)
                
                # Wait for login
                if bot.wait_for_login():
                    send_event('connected', 'Connected to WhatsApp')
                    
                    # Process queued messages
                    while True:
                        if MESSAGES_QUEUE and bot.connected:
                            msg = MESSAGES_QUEUE.pop(0)
                            if bot.send_message(msg['phone'], msg['message']):
                                send_event('message_sent', f"Message sent to {msg['phone']}")
                            time.sleep(2)  # Rate limiting
                        time.sleep(1)
                        
        except Exception as e:
            send_event('error', f'Bot error: {str(e)}')
    
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    return jsonify({'success': True})

@app.route('/stop_bot', methods=['POST'])
def stop_bot():
    """Stop the WhatsApp bot"""
    bot.close()
    return jsonify({'success': True})

@app.route('/send_message', methods=['POST'])
def send_message():
    """Add message to queue"""
    data = request.get_json()
    
    if 'phone' not in data or 'message' not in data:
        return jsonify({'success': False, 'error': 'Missing phone or message'})
    
    MESSAGES_QUEUE.append({
        'phone': data['phone'],
        'message': data['message'],
        'timestamp': time.time()
    })
    
    return jsonify({'success': True, 'queue_length': len(MESSAGES_QUEUE)})

@app.route('/get_queue')
def get_queue():
    """Get current message queue"""
    return jsonify({'queue': MESSAGES_QUEUE})

@app.route('/remove_from_queue', methods=['POST'])
def remove_from_queue():
    """Remove message from queue"""
    data = request.get_json()
    index = data.get('index')
    
    if 0 <= index < len(MESSAGES_QUEUE):
        MESSAGES_QUEUE.pop(index)
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'Invalid index'})

# Server-Sent Events for real-time updates
def send_event(event_type, message, qr_code=None):
    """Send SSE event to clients"""
    # In a real implementation, you'd use Flask-SSE or similar
    # This is a simplified version
    pass

@app.route('/events')
def events():
    """SSE endpoint"""
    def generate():
        # This would stream events in a real implementation
        yield f"data: {json.dumps({'type': 'status', 'message': 'Bot started'})}\n\n"
    
    return generate(), {'Content-Type': 'text/event-stream'}

if __name__ == '__main__':
    # Ensure required files exist
    if not os.path.exists('qr_code.png'):
        # Create a placeholder QR code
        qr = qrcode.QRCode()
        qr.add_data('Placeholder')
        qr.make()
        qr.make_image().save('qr_code.png')
    
    print("Starting WhatsApp Bot Dashboard...")
    print("Open http://localhost:5000 in your browser")
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)