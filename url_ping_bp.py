import requests
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
from flask import Blueprint, render_template, jsonify, request
import datetime
import json
import time
from colorama import Fore

url_ping_bp = Blueprint('url_ping', __name__, url_prefix='/lyxpinger')

# Store logs and status
ping_logs = []
url_status = {}
MAX_LOGS = 200  # Keep last 200 logs

target_urls = [
    'lyxnexus.onrender.com',
    'lyxnexus-3.onrender.com',
    'lyxspace.onrender.com',
    't-give-3.onrender.com/home',
    'lyxnexus.xo.je',
    'lyxnexus.lyxnexus.xo.je',
    'viewstream-1.onrender.com'
]

def ping_urls():
    headers = {
        'User-Agent': 'LyxLab-Ping-Service/1.02'
    }
    
    for u in target_urls:
        url = f'https://{u}'
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            start_time = time.time()
            response = requests.get(url, timeout=10, headers=headers)
            response_time = round(time.time() - start_time, 2)
            status_code = response.status_code
            
            log_message = {
                'timestamp': timestamp,
                'type': 'success',
                'url': url,
                'status_code': status_code,
                'response_time': response_time,
                'message': f"✅ SUCCESS: {url} | Status: {status_code} | Response: {response_time}s"
            }
            
            # Update URL status
            url_status[u] = {
                'status': 'online',
                'status_code': status_code,
                'last_checked': timestamp,
                'response_time': response_time,
                'url': url
            }
            
        except requests.exceptions.RequestException as e:
            log_message = {
                'timestamp': timestamp,
                'type': 'error',
                'url': url,
                'status_code': 'N/A',
                'response_time': 'N/A',
                'message': f"❌ FAILED: {url} | Error: {str(e)}"
            }
            
            # Update URL status
            url_status[u] = {
                'status': 'offline',
                'status_code': 'N/A',
                'last_checked': timestamp,
                'response_time': 'N/A',
                'url': url
            }
        
        # Add to logs and maintain max size
        ping_logs.append(log_message)
        if len(ping_logs) > MAX_LOGS:
            ping_logs.pop(0)
        
        print(log_message['message'])

@url_ping_bp.route('/')
def index():
    return render_template('admin_ping_url.html')

# API Endpoints
@url_ping_bp.route('/api/status')
def api_status():
    """Get current status of all URLs"""
    return jsonify({
        'urls': target_urls,
        'url_status': url_status,
        'stats': {
            'total_urls': len(target_urls),
            'online_count': len([s for s in url_status.values() if s.get('status') == 'online']),
            'offline_count': len([s for s in url_status.values() if s.get('status') == 'offline']),
            'last_update': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    })

@url_ping_bp.route('/api/logs')
def api_logs():
    """Get logs with pagination"""
    limit = min(int(request.args.get('limit', 50)), 100)
    offset = int(request.args.get('offset', 0))
    
    logs_slice = ping_logs[-limit-offset:][:limit] if offset > 0 else ping_logs[-limit:]
    
    return jsonify({
        'logs': list(reversed(logs_slice)),
        'total_logs': len(ping_logs),
        'limit': limit,
        'offset': offset
    })

@url_ping_bp.route('/api/ping-now', methods=['POST'])
def api_ping_now():
    """Manual ping endpoint"""
    ping_urls()
    return jsonify({
        'success': True,
        'message': 'Manual ping completed successfully',
        'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

@url_ping_bp.route('/api/clear-logs', methods=['POST'])
def api_clear_logs():
    """Clear all logs"""
    ping_logs.clear()
    return jsonify({
        'success': True,
        'message': 'All logs cleared successfully',
        'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

@url_ping_bp.route('/api/ping-specific', methods=['POST'])
def api_ping_specific():
    """Ping specific URL"""
    data = request.get_json()
    url_to_ping = data.get('url')
    
    if not url_to_ping:
        return jsonify({'success': False, 'message': 'URL parameter required'}), 400
    
    headers = {
        'User-Agent': 'LyxLab-Ping-Service/1.21'
    }
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        start_time = time.time()
        response = requests.get(url_to_ping, timeout=10, headers=headers)
        response_time = round(time.time() - start_time, 2)
        
        log_message = {
            'timestamp': timestamp,
            'type': 'success',
            'url': url_to_ping,
            'status_code': response.status_code,
            'response_time': response_time,
            'message': f"✅ MANUAL SUCCESS: {url_to_ping} | Status: {response.status_code} | Response: {response_time}s"
        }
        
        ping_logs.append(log_message)
        if len(ping_logs) > MAX_LOGS:
            ping_logs.pop(0)
        
        return jsonify({
            'success': True,
            'status': 'online',
            'status_code': response.status_code,
            'response_time': response_time,
            'message': log_message['message']
        })
        
    except requests.exceptions.RequestException as e:
        log_message = {
            'timestamp': timestamp,
            'type': 'error',
            'url': url_to_ping,
            'status_code': 'N/A',
            'response_time': 'N/A',
            'message': f"❌ MANUAL FAILED: {url_to_ping} | Error: {str(e)}"
        }
        
        ping_logs.append(log_message)
        if len(ping_logs) > MAX_LOGS:
            ping_logs.pop(0)
        
        return jsonify({
            'success': False,
            'status': 'offline',
            'status_code': 'N/A',
            'response_time': 'N/A',
            'message': log_message['message']
        }), 500

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=ping_urls, trigger="interval", minutes=3)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

# Perform initial ping
print("Starting initial ping...")
ping_urls()
print(Fore.GREEN + "✅ Ping URL Initialization success!.")