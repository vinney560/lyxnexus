"""
sms_service.py - Standalone SMS service with mock database
Usage: Import this file and use SMSDeliveryService class
"""

import time
import re
import threading
import http.client
import json
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Mock User Model
@dataclass
class MockUser:
    """Mock User model for testing"""
    id: int
    username: str
    mobile: str
    email: str
    is_active: bool = True
    
    @classmethod
    def query(cls):
        """Mock query method"""
        return MockQuery()
    
    @classmethod
    def filter(cls, *args, **kwargs):
        """Mock filter method"""
        return MockQuery()


class MockQuery:
    """Mock SQLAlchemy query"""
    
    def __init__(self):
        self.users = generate_mock_users()
    
    def all(self):
        return self.users
    
    def limit(self, n):
        return self.users[:n]
    
    def filter(self, *args, **kwargs):
        # Simplified filter logic
        filtered_users = []
        for user in self.users:
            if hasattr(args[0], 'left'):
                # Handle User.mobile.isnot(None)
                if user.mobile:
                    filtered_users.append(user)
            elif 'id' in kwargs:
                # Handle id in list
                if user.id in kwargs.get('id', []):
                    filtered_users.append(user)
        self.users = filtered_users
        return self


def generate_mock_users():
    """Generate mock user data for testing"""
    return [
        MockUser(1, "john_doe", "0740694312", "john@example.com"),
        MockUser(2, "jane_smith", "0768508448", "jane@example.com"),
    ]


class SMSDeliveryService:
    """SMS delivery service with rate limiting and error handling"""
    
    def __init__(self, api_key="d3dd8ae41cd64c6a89556876648e28f9", 
                 server_url="https://w2.endlessmessages.com"):
        self.api_key = api_key
        self.server_url = server_url
        self.server_host = self.server_url.replace("https://", "")
        self.rate_limit_delay = 6  # seconds between messages
        self.max_retries = 2
        self.test_mode = False  # Set to True for dry runs
        
    def format_phone_number(self, phone_number):
        """Convert phone number to +254 format"""
        if not phone_number:
            return None
            
        cleaned = re.sub(r'[\s\-\(\)]', '', str(phone_number))
        
        if cleaned.startswith('07') and len(cleaned) == 10:
            return f"+254{cleaned[1:]}"
        elif cleaned.startswith('7') and len(cleaned) == 9:
            return f"+254{cleaned}"
        elif cleaned.startswith('+254') and len(cleaned) == 13:
            return cleaned
        elif cleaned.startswith('254') and len(cleaned) == 12:
            return f"+{cleaned}"
        elif cleaned.startswith('0'):
            return f"+254{cleaned[1:]}"
        else:
            return cleaned if cleaned.startswith('+') else f"+{cleaned}"
    
    def validate_phone_number(self, phone_number):
        """Validate if phone number is in correct format"""
        formatted = self.format_phone_number(phone_number)
        if formatted and formatted.startswith('+254') and len(formatted) == 13:
            # Additional validation for Kenyan numbers
            return formatted[4:].isdigit()
        return False
    
    def send_single_sms(self, phone_number, message, priority=0, retry_count=0):
        """Send SMS to a single recipient with retry logic"""
        
        if self.test_mode:
            logger.info(f"TEST MODE: Would send to {phone_number}: {message[:50]}...")
            return {
                'success': True,
                'status_code': 200,
                'phone': phone_number,
                'formatted': self.format_phone_number(phone_number),
                'timestamp': datetime.now().isoformat(),
                'response': '{"status": "success", "message": "Test mode - no actual SMS sent"}'
            }
        
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
        
        logger.info(f"Starting bulk SMS send to {len(user_list)} users")
        
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
                    logger.warning(f"No phone for {username}")
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
                    logger.warning(f"Invalid phone for {username}: {phone}")
                    continue
                
                # Send SMS with rate limiting
                logger.info(f"Sending to {username} ({phone}) - {index + 1}/{len(user_list)}")
                time.sleep(self.rate_limit_delay)
                result = self.send_single_sms(phone, message)
                
                # Add username to result
                result['username'] = username
                
                if result['success']:
                    results['successful'] += 1
                    logger.info(f"Successfully sent to {username}")
                else:
                    results['failed'] += 1
                    logger.error(f"Failed to send to {username}: {result.get('error', 'Unknown error')}")
                
                results['details'].append(result)
                
                # Call callback if provided
                if callback:
                    callback(result)
                
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
                logger.error(f"Exception sending to user: {str(e)}")
        
        logger.info(f"Bulk SMS completed: {results['successful']} successful, "
                   f"{results['failed']} failed, {results['invalid_numbers']} invalid")
        
        return results

    def send_to_all_users(self, message, batch_size=50, test_mode=False):
        """Send SMS to all users in database in batches"""
        self.test_mode = test_mode
        
        try:
            # Get all users with mobile numbers
            users = MockUser.query().filter(MockUser.mobile.isnot(None)).all()
            
            total_users = len(users)
            logger.info(f"Found {total_users} users with mobile numbers")
            
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
                logger.info(f"Processing batch {i // batch_size + 1} with {len(batch)} users")
                
                batch_result = self.send_bulk_sms(batch, message)
                
                results['successful'] += batch_result['successful']
                results['failed'] += batch_result['failed']
                results['invalid_numbers'] += batch_result['invalid_numbers']
                results['batches'].append({
                    'batch_number': i // batch_size + 1,
                    'results': batch_result
                })
                
                logger.info(
                    f"Batch {i // batch_size + 1} completed: "
                    f"{batch_result['successful']} successful, "
                    f"{batch_result['failed']} failed"
                )
            
            return results
            
        except Exception as e:
            logger.error(f"Error in send_to_all_users: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'total': 0,
                'successful': 0,
                'failed': 0
            }


# Helper functions for easy integration
def send_immediate_sms(phone_number, message):
    """Quick function to send immediate SMS"""
    service = SMSDeliveryService()
    return service.send_single_sms(phone_number, message)


def send_bulk_sms_to_users(users, message):
    """Quick function to send bulk SMS"""
    service = SMSDeliveryService()
    return service.send_bulk_sms(users, message)


def run_demo():
    """Run a demonstration of the SMS service"""
    print("=" * 60)
    print("SMS Service Demo")
    print("=" * 60)
    
    # Create service instance
    service = SMSDeliveryService()
    
    # Test single SMS
    print("\n1. Testing single SMS:")
    result = service.send_single_sms("0740694312",
        "*Title*"
        "\nThis is a test message sent via the SMSDeliveryService.")
    print(f"   Success: {result['success']}")
    print(f"   To: {result.get('formatted', 'N/A')}")
    
    # Test bulk SMS
    print("\n2. Testing bulk SMS with mock users:")
    users = generate_mock_users()[:5]  # First 5 users
    results = service.send_bulk_sms(users, "Bulk test message")
    
    print(f"   Total: {results['total']}")
    print(f"   Successful: {results['successful']}")
    print(f"   Failed: {results['failed']}")
    print(f"   Invalid numbers: {results['invalid_numbers']}")
    
    # Test all users
    print("\n3. Testing send to all users (test mode):")
    results = service.send_to_all_users("Newsletter update!", test_mode=True)
    
    print(f"   Total users: {results['total']}")
    print(f"   Successful: {results['successful']}")
    print(f"   Failed: {results['failed']}")
    
    print("\n" + "=" * 60)
    print("Demo completed!")
    print("=" * 60)


if __name__ == "__main__":
    # Run demo when script is executed directly
    run_demo()