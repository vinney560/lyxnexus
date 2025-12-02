"""
whatsapp_service.py - Simple WhatsApp sender for 2 numbers
Usage: python whatsapp_service.py
"""

import time
import re
import http.client
import json
import random
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WhatsAppSender:
    """Simple WhatsApp sender for 2 mobile numbers"""
    
    def __init__(self, api_key="d3dd8ae41cd64c6a89556876648e28f9"):
        self.api_key = api_key
        self.server_host = "w2.endlessmessages.com"
        self.base_delay = 0.3  # 300ms for WhatsApp
        self.random_variance = 0.2  # ±200ms random
        
    def format_phone(self, phone):
        """Format phone to +254"""
        if not phone:
            return None
            
        # Remove all non-digits
        digits = re.sub(r'\D', '', str(phone))
        
        if not digits:
            return None
            
        # If starts with 0, remove it
        if digits.startswith('0'):
            digits = digits[1:]
        
        # If 9 digits, add +254
        if len(digits) == 9:
            return f"+254{digits}"
        
        # If 12 digits (254XXXXXXXXX), add +
        if len(digits) == 12 and digits.startswith('254'):
            return f"+{digits}"
        
        # Default: take last 9 digits and add +254
        if len(digits) >= 9:
            return f"+254{digits[-9:]}"
        
        return None
    
    def format_whatsapp_message(self, title, description, link=None):
        """Format message for WhatsApp with proper styling"""
        
        message = f"""*📢 {title}*

{description}

"""
        
        if link:
            message += f"🔗 *Link:* {link}\n\n"
        
        message += "_Sent via University Announcements System_"
        
        return message
    
    def send_single(self, phone, message):
        """Send WhatsApp to one number"""
        formatted_phone = self.format_phone(phone)
        
        if not formatted_phone:
            return {"success": False, "error": "Invalid phone number"}
        
        print(f"📤 Sending to: {phone} -> {formatted_phone}")
        print(f"📝 Message: {message[:100]}...")
        
        payload = {
            "number": formatted_phone,
            "apikey": self.api_key,
            "text": message,
            "fileData": "",
            "fileName": "",
            "priority": 1,  # WhatsApp priority
            "scheduledDate": ""
        }
        
        try:
            conn = http.client.HTTPSConnection(self.server_host, timeout=30)
            conn.request("POST", "/send_message", json.dumps(payload), 
                        {'Content-Type': 'application/json'})
            
            res = conn.getresponse()
            data = res.read()
            response_text = data.decode("utf-8")
            conn.close()
            
            # Parse response
            success = False
            try:
                response_json = json.loads(response_text)
                success = response_json.get('status', '').lower() in ['success', 'sent', 'queued']
            except:
                success = any(keyword in response_text.lower() 
                            for keyword in ['success', 'sent', 'message queued'])
            
            result = {
                'success': success,
                'status_code': res.status,
                'phone': phone,
                'formatted': formatted_phone,
                'response': response_text[:200]
            }
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'phone': phone,
                'formatted': formatted_phone
            }
    
    def send_to_two_numbers(self, phone1, phone2, message):
        """Send WhatsApp to both numbers with delay"""
        results = []
        
        phones = [phone1, phone2]
        
        for i, phone in enumerate(phones):
            print(f"\n[{i+1}/2] Processing {phone}")
            
            # Send message
            result = self.send_single(phone, message)
            results.append(result)
            
            if result['success']:
                print(f"✅ Sent to {phone}")
            else:
                print(f"❌ Failed: {result.get('error', 'Unknown')}")
            
            # Add delay between messages (for WhatsApp anti-ban)
            if i < len(phones) - 1:
                delay = self.base_delay + random.uniform(-self.random_variance, self.random_variance)
                delay = max(0.15, delay)  # Minimum 150ms
                print(f"⏳ Waiting {delay:.2f}s...")
                time.sleep(delay)
        
        return results
    
    def send_announcement(self, phone1, phone2, title, description, link=None):
        """Send formatted announcement to both numbers"""
        # Format message for WhatsApp
        message = self.format_whatsapp_message(title, description, link)
        
        print("=" * 60)
        print("📱 WHATSAPP ANNOUNCEMENT")
        print("=" * 60)
        print(f"Title: {title}")
        print(f"Description: {description[:100]}...")
        if link:
            print(f"Link: {link}")
        print(f"Recipients: {phone1}, {phone2}")
        print("=" * 60)
        
        # Send to both numbers
        return self.send_to_two_numbers(phone1, phone2, message)

# ==================== SAMPLE ANNOUNCEMENTS ====================
SAMPLE_ANNOUNCEMENTS = [
    {
        "title": "EXAMINATION TIMETABLE RELEASED",
        "description": "The end of semester examination timetable has been released. Please check the student portal for your schedule. All exams will be held in the main examination halls.",
        "link": "https://portal.university.ac.ke/exams"
    },
    {
        "title": "FEE PAYMENT REMINDER",
        "description": "This is a reminder that the fee payment deadline is 30th November 2025. Late payments will attract a penalty. Please clear your fees to avoid inconvenience.",
        "link": "https://portal.university.ac.ke/fees"
    },
    {
        "title": "GRADUATION CEREMONY",
        "description": "The 24th Graduation Ceremony will be held on 12th December 2025. All graduating students must attend the rehearsal on 10th December.",
        "link": None
    }
]

# ==================== MAIN EXECUTION ====================
def main():
    """Main function to send WhatsApp announcements"""
    
    print("🚀 WhatsApp Announcement Sender")
    print("=" * 60)
    
    # The two mobile numbers
    PHONE1 = "0740694312"
    PHONE2 = "0768508448"
    
    print(f"📱 Number 1: {PHONE1}")
    print(f"📱 Number 2: {PHONE2}")
    print("=" * 60)
    
    # Create WhatsApp sender
    sender = WhatsAppSender()
    
    # Test phone formatting
    print("\n🔧 Phone Formatting Test:")
    for phone in [PHONE1, PHONE2]:
        formatted = sender.format_phone(phone)
        print(f"  {phone} -> {formatted}")
    
    # Ask user which announcement to send
    print("\n📋 Available Announcements:")
    for i, announcement in enumerate(SAMPLE_ANNOUNCEMENTS, 1):
        print(f"{i}. {announcement['title']}")
    
    print(f"{len(SAMPLE_ANNOUNCEMENTS) + 1}. Custom announcement")
    
    choice = input("\nSelect announcement (1-4): ").strip()
    
    if choice == "4":
        # Custom announcement
        title = input("Enter title: ").strip()
        description = input("Enter description: ").strip()
        link = input("Enter link (press Enter to skip): ").strip() or None
        
        if not title or not description:
            print("❌ Title and description are required!")
            return
    else:
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(SAMPLE_ANNOUNCEMENTS):
                announcement = SAMPLE_ANNOUNCEMENTS[idx]
                title = announcement["title"]
                description = announcement["description"]
                link = announcement["link"]
            else:
                print("❌ Invalid choice!")
                return
        except:
            print("❌ Invalid input!")
            return
    
    # Confirm before sending
    print("\n" + "=" * 60)
    print("📤 READY TO SEND")
    print("=" * 60)
    print(f"Title: {title}")
    print(f"Description: {description[:100]}...")
    if link:
        print(f"Link: {link}")
    print(f"To: {PHONE1}, {PHONE2}")
    
    confirm = input("\nSend this announcement? (yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("❌ Cancelled!")
        return
    
    # Send the announcement
    print("\n" + "=" * 60)
    print("📨 SENDING ANNOUNCEMENT...")
    print("=" * 60)
    
    results = sender.send_announcement(PHONE1, PHONE2, title, description, link)
    
    # Show results
    print("\n" + "=" * 60)
    print("📊 RESULTS")
    print("=" * 60)
    
    success_count = sum(1 for r in results if r['success'])
    
    for i, result in enumerate(results, 1):
        status = "✅ SUCCESS" if result['success'] else "❌ FAILED"
        print(f"\nRecipient {i}: {result['phone']}")
        print(f"  Status: {status}")
        if not result['success']:
            print(f"  Error: {result.get('error', 'Unknown')}")
    
    print(f"\n📈 Summary: {success_count}/2 successful")
    
    # Save log
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "title": title,
        "description": description[:100],
        "link": link,
        "recipients": [PHONE1, PHONE2],
        "results": results,
        "success_rate": f"{success_count}/2"
    }
    
    # Save to log file
    try:
        with open("whatsapp_log.json", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        print(f"\n📝 Log saved to whatsapp_log.json")
    except:
        print(f"\n⚠️ Could not save log file")

# Quick send function (for importing)
def quick_send(title, description, link=None):
    """Quick function to send announcement to both numbers"""
    PHONE1 = "0740694312"
    PHONE2 = "0768508448"
    
    sender = WhatsAppSender()
    return sender.send_announcement(PHONE1, PHONE2, title, description, link)

if __name__ == "__main__":
    main()