# ==================== SMS SERVICE INTEGRATION ====================
import time
import re
import threading
import http.client
import json
from datetime import datetime
from functools import wraps
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

class SMSDeliveryService:
    """SMS delivery service with rate limiting and error handling"""
    
    def __init__(self, api_key=None, server_url=None):
        self.api_key = api_key or current_app.config.get('SMS_API_KEY', 'd3dd8ae41cd64c6a89556876648e28f9')
        self.server_url = server_url or current_app.config.get('SMS_SERVER_URL', 'https://w2.endlessmessages.com')
        self.server_host = self.server_url.replace("https://", "")
        self.rate_limit_delay = 6  # seconds between messages
        self.max_retries = 2
        
    def format_phone_number(self, phone_number):
        """Convert phone number to +254 format (supports 01 and 07)"""
        if not phone_number:
            return None
            
        cleaned = re.sub(r'[\s\-\(\)]', '', str(phone_number))
        
        # Handle 01XXXXXXXX (10 digits) - typically landlines
        if cleaned.startswith('01') and len(cleaned) == 10:
            return f"+254{cleaned[1:]}"  # Replace 0 with +254
        # Handle 07XXXXXXXX (10 digits) - typically mobiles
        elif cleaned.startswith('07') and len(cleaned) == 10:
            return f"+254{cleaned[1:]}"  # Replace 0 with +254
        # Handle 1XXXXXXXX (9 digits) - missing leading 0
        elif cleaned.startswith('1') and len(cleaned) == 9:
            return f"+254{cleaned}"
        # Handle 7XXXXXXXX (9 digits) - missing leading 0
        elif cleaned.startswith('7') and len(cleaned) == 9:
            return f"+254{cleaned}"
        # Already in +254 format
        elif cleaned.startswith('+254') and len(cleaned) == 13:
            return cleaned
        # 254 format without +
        elif cleaned.startswith('254') and len(cleaned) == 12:
            return f"+{cleaned}"
        # Any other number starting with 0
        elif cleaned.startswith('0'):
            return f"+254{cleaned[1:]}"
        else:
            return cleaned if cleaned.startswith('+') else f"+{cleaned}"
    
    def validate_phone_number(self, phone_number):
        """Validate if phone number is in correct format (supports both 01 and 07)"""
        formatted = self.format_phone_number(phone_number)
        if formatted and formatted.startswith('+254') and len(formatted) == 13:
            # Check if it's a valid Kenyan number (starts with +2541 or +2547)
            return formatted[4:].isdigit() and formatted[3] in ['1', '7']
        return False
    
    def send_single_sms(self, phone_number, message, priority=0, retry_count=0):
        """Send SMS to a single recipient with retry logic"""
        formatted_number = self.format_phone_number(phone_number)
        
        if not formatted_number or not self.validate_phone_number(phone_number):
            return {
                'success': False,
                'error': 'Invalid phone number format',
                'phone': phone_number,
                'formatted': formatted_number
            }
        
        payload = {
            "number": formatted_number,
            "apikey": self.api_key,
            "text": message[:160],  # Truncate to 160 chars
            "fileData": "",
            "fileName": "",
            "priority": priority,
            "scheduledDate": ""
        }
        
        try:
            conn = http.client.HTTPSConnection(self.server_host)
            conn.request("POST", "/send_message", json.dumps(payload), 
                        {'Content-Type': 'application/json'})
            
            res = conn.getresponse()
            data = res.read()
            response_text = data.decode("utf-8")
            conn.close()
            
            success = res.status in [200, 201]
            
            result = {
                'success': success,
                'status_code': res.status,
                'phone': phone_number,
                'formatted': formatted_number,
                'timestamp': datetime.now().isoformat(),
                'response': response_text
            }
            
            # Retry logic for failed attempts
            if not success and retry_count < self.max_retries:
                time.sleep(2)  # Wait before retry
                return self.send_single_sms(phone_number, message, priority, retry_count + 1)
                
            return result
            
        except Exception as e:
            if retry_count < self.max_retries:
                time.sleep(2)
                return self.send_single_sms(phone_number, message, priority, retry_count + 1)
            
            return {
                'success': False,
                'error': str(e),
                'phone': phone_number,
                'formatted': formatted_number,
                'timestamp': datetime.now().isoformat()
            }
    
    def send_bulk_sms(self, user_list, message, callback=None):
        """
        Send SMS to multiple users with rate limiting
        
        Args:
            user_list: List of User objects or dictionaries with 'mobile' key
            message: SMS message to send
            callback: Optional callback function to handle results
        """
        results = {
            'total': len(user_list),
            'successful': 0,
            'failed': 0,
            'invalid_numbers': 0,
            'details': []
        }
        
        for index, user in enumerate(user_list):
            try:
                # Extract phone number from User object or dict
                if hasattr(user, 'mobile'):
                    phone = user.mobile
                    username = user.username if hasattr(user, 'username') else 'N/A'
                elif isinstance(user, dict):
                    phone = user.get('mobile')
                    username = user.get('username', 'N/A')
                else:
                    continue
                
                # Skip if no phone number
                if not phone:
                    result = {
                        'success': False,
                        'error': 'No phone number',
                        'username': username,
                        'phone': phone,
                        'timestamp': datetime.now().isoformat()
                    }
                    results['details'].append(result)
                    results['failed'] += 1
                    continue
                
                # Validate phone number
                if not self.validate_phone_number(phone):
                    result = {
                        'success': False,
                        'error': 'Invalid phone format',
                        'username': username,
                        'phone': phone,
                        'timestamp': datetime.now().isoformat()
                    }
                    results['details'].append(result)
                    results['invalid_numbers'] += 1
                    continue
                
                # Send SMS with rate limiting
                time.sleep(self.rate_limit_delay)
                result = self.send_single_sms(phone, message)
                
                # Add username to result
                result['username'] = username
                
                if result['success']:
                    results['successful'] += 1
                else:
                    results['failed'] += 1
                
                results['details'].append(result)
                
                # Call callback if provided
                if callback:
                    callback(result)
                
                # Log progress
                current_app.logger.info(
                    f"SMS Progress: {index + 1}/{len(user_list)} - "
                    f"{username}: {'Success' if result['success'] else 'Failed'}"
                )
                
            except Exception as e:
                error_result = {
                    'success': False,
                    'error': str(e),
                    'username': username if 'username' in locals() else 'Unknown',
                    'phone': phone if 'phone' in locals() else 'Unknown',
                    'timestamp': datetime.now().isoformat()
                }
                results['details'].append(error_result)
                results['failed'] += 1
        
        return results

    def send_to_all_users(self, message, batch_size=50):
        """Send SMS to all users in database in batches"""
        try:
            # Get all users with mobile numbers (both 01 and 07)
            users = User.query.filter(User.mobile.isnot(None)).all()
            
            total_users = len(users)
            results = {
                'total': total_users,
                'successful': 0,
                'failed': 0,
                'invalid_numbers': 0,
                'batches': []
            }
            
            # Process in batches
            for i in range(0, total_users, batch_size):
                batch = users[i:i + batch_size]
                batch_result = self.send_bulk_sms(batch, message)
                
                results['successful'] += batch_result['successful']
                results['failed'] += batch_result['failed']
                results['invalid_numbers'] += batch_result['invalid_numbers']
                results['batches'].append({
                    'batch_number': i // batch_size + 1,
                    'results': batch_result
                })
                
                current_app.logger.info(
                    f"Batch {i // batch_size + 1} completed: "
                    f"{batch_result['successful']} successful, "
                    f"{batch_result['failed']} failed"
                )
            
            return results
            
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error in send_to_all_users: {str(e)}")
            return {
                'success': False,
                'error': f"Database error: {str(e)}",
                'total': 0,
                'successful': 0,
                'failed': 0
            }


# Thread-safe SMS service instance
_sms_service = None

def get_sms_service():
    """Get or create SMS service instance (thread-safe)"""
    global _sms_service
    if _sms_service is None:
        _sms_service = SMSDeliveryService()
    return _sms_service


# Flask route decorators and helpers
def async_sms_task(f):
    """Decorator to run SMS tasks in background thread"""
    @wraps(f)
    def decorated(*args, **kwargs):
        thread = threading.Thread(target=f, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        return thread
    return decorated


# ==================== SIMPLE TRIGGER FUNCTIONS ====================

def single_message(user_id, message="Default message"):
    """
    Send SMS to a single user by user ID
    
    Usage:
        single_message(1, "Hello John!")  # Send to user with ID 1
        single_message(user.id, "Your order is ready!")
    """
    try:
        user = User.query.get(user_id)
        if not user:
            return {"status": "error", "message": f"User with ID {user_id} not found"}
        
        if not user.mobile:
            return {"status": "error", "message": f"User {user.username} has no mobile number"}
        
        @async_sms_task
        def send_background():
            sms_service = get_sms_service()
            result = sms_service.send_single_sms(user.mobile, message)
            current_app.logger.info(f"Single SMS to {user.username}: {'Success' if result['success'] else 'Failed'}")
            return result
        
        send_background()
        return {
            "status": "started", 
            "user": user.username,
            "mobile": user.mobile,
            "formatted": get_sms_service().format_phone_number(user.mobile)
        }
        
    except Exception as e:
        current_app.logger.error(f"Error in single_message: {str(e)}")
        return {"status": "error", "message": str(e)}


def bulk_message(message="Default message", user_ids=None):
    """
    Send SMS to multiple users
    
    Usage:
        bulk_message("Hello users!")  # Send to all users
        bulk_message("Special offer!", [1, 2, 3])  # Send to specific user IDs
    """
    try:
        if user_ids:
            users = User.query.filter(User.id.in_(user_ids)).all()
        else:
            users = User.query.filter(User.mobile.isnot(None)).all()
        
        @async_sms_task
        def send_background():
            sms_service = get_sms_service()
            results = sms_service.send_bulk_sms(users, message)
            current_app.logger.info(f"Bulk SMS completed: {len(users)} users")
            return results
        
        send_background()
        return {"status": "started", "total_users": len(users)}
        
    except Exception as e:
        current_app.logger.error(f"Error in bulk_message: {str(e)}")
        return {"status": "error", "message": str(e)}


def send_to_phone(phone_number, message):
    """
    Send SMS directly to a phone number (bypasses User model)
    
    Usage:
        send_to_phone("0712345678", "Your OTP is 123456")
        send_to_phone("0123456789", "Appointment reminder")
    """
    try:
        @async_sms_task
        def send_background():
            sms_service = get_sms_service()
            result = sms_service.send_single_sms(phone_number, message)
            formatted = sms_service.format_phone_number(phone_number)
            current_app.logger.info(f"SMS to {formatted}: {'Success' if result['success'] else 'Failed'}")
            return result
        
        send_background()
        return {
            "status": "started", 
            "phone": phone_number,
            "formatted": get_sms_service().format_phone_number(phone_number)
        }
        
    except Exception as e:
        current_app.logger.error(f"Error in send_to_phone: {str(e)}")
        return {"status": "error", "message": str(e)}


# ==================== API ENDPOINTS ====================

@app.route('/send-single-sms', methods=['POST'])
def send_single_sms_route():
    """API endpoint to send single SMS"""
    from flask import request, jsonify
    
    data = request.get_json()
    message = data.get('message')
    user_id = data.get('user_id')
    phone = data.get('phone')
    
    if not message:
        return jsonify({'error': 'Message is required'}), 400
    
    if user_id:
        # Send to user by ID
        result = single_message(user_id, message)
    elif phone:
        # Send directly to phone number
        result = send_to_phone(phone, message)
    else:
        return jsonify({'error': 'Either user_id or phone is required'}), 400
    
    if result['status'] == 'started':
        return jsonify({
            'message': 'SMS sending started in background',
            'data': result
        }), 202
    else:
        return jsonify({'error': result['message']}), 500


@app.route('/send-bulk-sms', methods=['POST'])
def send_bulk_sms_route():
    """API endpoint to send bulk SMS"""
    from flask import request, jsonify
    
    data = request.get_json()
    message = data.get('message')
    user_ids = data.get('user_ids', [])
    
    if not message:
        return jsonify({'error': 'Message is required'}), 400
    
    # Use the simple bulk_message function
    result = bulk_message(message, user_ids if user_ids else None)
    
    if result['status'] == 'started':
        return jsonify({
            'message': 'SMS sending started in background',
            'total_users': result['total_users']
        }), 202
    else:
        return jsonify({'error': result['message']}), 500


@app.route('/sms-status', methods=['GET'])
def get_sms_status():
    """Endpoint to check SMS delivery status (mock implementation)"""
    return jsonify({
        'status': 'service_running',
        'last_checked': datetime.now().isoformat()
    })


# Command line interface for manual SMS sending
@app.cli.command('send-sms')
def send_sms_command():
    """CLI command to send SMS to users"""
    import click
    
    @click.command()
    @click.option('--message', prompt='Enter message', help='SMS message to send')
    @click.option('--user-id', type=int, help='Send to specific user ID')
    @click.option('--phone', help='Send directly to phone number')
    @click.option('--all-users', is_flag=True, help='Send to all users')
    @click.option('--test', is_flag=True, help='Test mode (dry run)')
    def send_sms(message, user_id, phone, all_users, test):
        """Send SMS to users"""
        if test:
            click.echo(f"Test mode: Would send: '{message}'")
            
            if user_id:
                user = User.query.get(user_id)
                if user:
                    formatted = get_sms_service().format_phone_number(user.mobile)
                    click.echo(f"To User {user_id} ({user.username}): {user.mobile} -> {formatted}")
            
            if phone:
                formatted = get_sms_service().format_phone_number(phone)
                click.echo(f"To Phone: {phone} -> {formatted}")
            
            if all_users:
                users = User.query.filter(User.mobile.isnot(None)).limit(3).all()
                for user in users:
                    formatted = get_sms_service().format_phone_number(user.mobile)
                    click.echo(f"To All: {user.username} ({user.mobile}) -> {formatted}")
        else:
            if user_id:
                result = single_message(user_id, message)
                click.echo(f"SMS started for user ID {user_id}: {result}")
            elif phone:
                result = send_to_phone(phone, message)
                click.echo(f"SMS started for phone {phone}: {result}")
            elif all_users:
                result = bulk_message(message)
                click.echo(f"SMS started for all users: {result}")
            else:
                click.echo("Please specify --user-id, --phone, or --all-users")
    
    send_sms()
# ==================== END SMS SERVICE ====================