from flask import Flask, render_template, request, jsonify, send_from_directory, Blueprint
import requests
import json
from datetime import datetime

notification_bp = Blueprint('notification_c', __name__, url_prefix='/not')

# Store user tokens (in production, use a database)
user_tokens = []

# Firebase configuration
FIREBASE_SERVER_KEY = "AIzaSyDiySIsbCQ-uNEuqu3ZT1wFUkWkdwD7cbw"  # Your Server Key
FCM_URL = "https://fcm.googleapis.com/fcm/send"

@notification_bp.route('/')
def index():
    return render_template('notification.html')

@notification_bp.route('/firebase-messaging-sw.js')
def sw():
    return send_from_directory('static', 'firebase-messaging-sw.js', mimetype='application/javascript')

@notification_bp.route('/sw.js')
def swd():
    return send_from_directory('static', 'firebase-messaging-sw.js', mimetype='application/javascript')
@notification_bp.route('/save-token', methods=['POST'])
def save_token():
    try:
        data = request.get_json()
        token = data.get('token')
        
        if token and token not in user_tokens:
            user_tokens.append(token)
            print(f"✅ New token saved. Total users: {len(user_tokens)}")
            return jsonify({'success': True, 'message': 'Token saved successfully'})
        elif token in user_tokens:
            return jsonify({'success': True, 'message': 'Token already exists'})
        else:
            return jsonify({'success': False, 'message': 'Invalid token'})
            
    except Exception as e:
        print(f"❌ Error saving token: {e}")
        return jsonify({'success': False, 'message': str(e)})

@notification_bp.route('/send-notification', methods=['POST'])
def send_notification():
    try:
        data = request.get_json()
        title = data.get('title', 'Notification from Lyx Nexus')
        body = data.get('body', 'You have a new message!')
        token = data.get('token', '')
        
        if not token:
            return jsonify({'success': False, 'message': 'No token provided'})
        
        headers = {
            'Authorization': f'key={FIREBASE_SERVER_KEY}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'to': token,
            'notification': {
                'title': title,
                'body': body,
                'icon': 'https://lyxnexus.onrender.com/static/icon.png'
            },
            'data': {
                'timestamp': datetime.now().isoformat(),
                'url': 'https://lyxnexus.onrender.com'
            }
        }
        
        response = requests.post(FCM_URL, headers=headers, data=json.dumps(payload))
        
        if response.status_code == 200:
            print(f"✅ Notification sent to user")
            return jsonify({'success': True, 'message': 'Notification sent successfully'})
        else:
            print(f"❌ Failed to send notification: {response.text}")
            return jsonify({'success': False, 'message': f'Failed to send: {response.text}'})
            
    except Exception as e:
        print(f"❌ Error sending notification: {e}")
        return jsonify({'success': False, 'message': str(e)})

@notification_bp.route('/send-to-all', methods=['POST'])
def send_to_all():
    try:
        data = request.get_json()
        title = data.get('title', 'Notification from Lyx Nexus')
        body = data.get('body', 'You have a new message!')
        
        if not user_tokens:
            return jsonify({'success': False, 'message': 'No users registered'})
        
        success_count = 0
        failed_count = 0
        
        for token in user_tokens:
            headers = {
                'Authorization': f'key={FIREBASE_SERVER_KEY}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'to': token,
                'notification': {
                    'title': title,
                    'body': body,
                    'icon': 'https://lyxnexus.onrender.com/uploads/favicon.png'
                }
            }
            
            response = requests.post(FCM_URL, headers=headers, data=json.dumps(payload))
            
            if response.status_code == 200:
                success_count += 1
            else:
                failed_count += 1
        
        message = f"Sent {success_count} notifications successfully"
        if failed_count > 0:
            message += f", {failed_count} failed"
            
        print(f"📤 Sent to all: {success_count} success, {failed_count} failed")
        return jsonify({'success': True, 'message': message})
        
    except Exception as e:
        print(f"❌ Error sending to all: {e}")
        return jsonify({'success': False, 'message': str(e)})

@notification_bp.route('/get-tokens', methods=['GET'])
def get_tokens():
    try:
        tokens_preview = [token[:20] + '...' for token in user_tokens]
        return jsonify({
            'success': True,
            'tokens': tokens_preview,
            'count': len(user_tokens)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
