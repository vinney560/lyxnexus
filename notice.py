from flask import Flask, request, jsonify, render_template
from notificationapi_python_server_sdk import notificationapi
import asyncio
import os
from datetime import datetime

app = Flask(__name__)

# Initialize NotificationAPI
notificationapi.init(
    "tn46tvp8r580do0ei9jujqhe75",  # Client ID
    "taf382qxy2x7yt2270q1gnf7kurz1pjkxgwmf8lntt3qjww2cvsvz536gv"  # Client Secret
)

# Serve the call.html template
@app.route('/')
def serve_call_html():
    return render_template('call.html')

@app.route('/send-notification', methods=['POST'])
def send_notification():
    try:
        # Get notification data from request
        data = request.get_json()
        
        # Extract mobile and message from request
        mobile_number = data.get('mobile', '+254740123455')
        message_content = data.get('message', 'Hello, world!')
        
        # Log the request
        print(f"[{datetime.now()}] Sending notification to: {mobile_number}")
        print(f"Message: {message_content[:100]}...")
        
        # Prepare notification payload with dynamic data
        notification_payload = {
            "type": "announce",
            "to": {
                "id": "pushify_user",
                "number": mobile_number
            },
            "sms": {
                "message": f"SMS: {message_content}"
            },
            "call": {
                "message": f"Voice Call: {message_content}"
            }
        }
        
        # Send notification asynchronously
        async def send_async():
            return await notificationapi.send(notification_payload)
        
        response = asyncio.run(send_async())
        
        # Prepare response data
        response_data = {
            "success": True,
            "message": "Notification sent successfully",
            "data": {
                "to": mobile_number,
                "timestamp": datetime.now().isoformat(),
                "message_preview": message_content[:50] + "..." if len(message_content) > 50 else message_content
            },
            "response": {
                "status_code": getattr(response, 'status_code', 'N/A'),
                "status": getattr(response, 'reason', 'N/A') if hasattr(response, 'reason') else 'Sent'
            }
        }
        
        # Add full response text if available
        if hasattr(response, 'text'):
            response_data["response"]["text"] = response.text
        
        return jsonify(response_data), 200
        
    except Exception as e:
        error_data = {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "suggestion": "Check if the phone number is valid and you have sufficient credits."
        }
        print(f"[ERROR] {datetime.now()}: {str(e)}")
        return jsonify(error_data), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "Pushify Notification API",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "/": "HTML Interface",
            "/send-notification": "Send notifications (POST)",
            "/health": "Health check"
        }
    }), 200

@app.route('/test-numbers', methods=['GET'])
def get_test_numbers():
    """Return list of test phone numbers"""
    return jsonify({
        "test_numbers": [
            {"number": "+254740123455", "description": "Kenyan number (example)"},
            {"number": "+15005550006", "description": "NotificationAPI test number"},
            {"number": "+254712345678", "description": "Kenyan test format"}
        ],
        "note": "Use valid international format: +[country code][number]"
    })

if __name__ == '__main__':
    # Create call.html if it doesn't exist
    if not os.path.exists('call.html'):
        print("Warning: call.html not found in current directory")
        print("Please save the HTML template as 'call.html' in the same folder")
    
    print("=" * 50)
    print("Pushify Notification Server")
    print("=" * 50)
    print(f"Server starting on: http://localhost:5001")
    print(f"HTML Interface: http://localhost:5001")
    print(f"API Endpoint: http://localhost:5001/send-notification")
    print(f"Health Check: http://localhost:5001/health")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)