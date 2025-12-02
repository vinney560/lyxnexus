import requests
import re

class TextMeBotSMS:
    def __init__(self, api_key):
        """
        Initialize the SMS sender with your API key
        
        Args:
            api_key (str): Your TextMeBot API key
        """
        self.api_key = api_key
        self.base_url = "http://api.textmebot.com/send.php"
    
    def format_phone_number(self, phone_number):
        """
        Convert phone number from 07XXXXXXXX to +2547XXXXXXXX format
        
        Args:
            phone_number (str): Phone number in various formats
            
        Returns:
            str: Formatted phone number in +2547XXXXXXXX format
        """
        # Remove any spaces, dashes, or parentheses
        cleaned = re.sub(r'[\s\-\(\)]', '', str(phone_number))
        
        # If number starts with 07 (Kenya mobile format)
        if cleaned.startswith('07') and len(cleaned) == 10:
            return f"+254{cleaned[1:]}"  # Replace 0 with +254
        # If number already starts with +254
        elif cleaned.startswith('+254') and len(cleaned) == 13:
            return cleaned
        # If number starts with 254 (without +)
        elif cleaned.startswith('254') and len(cleaned) == 12:
            return f"+{cleaned}"
        # If number starts with 0 but not 07 (like 011 for landlines)
        elif cleaned.startswith('0'):
            return f"+254{cleaned[1:]}"
        else:
            # Return as is if format is not recognized
            return cleaned
    
    def send_sms(self, phone_number, message):
        """
        Send SMS to the specified phone number
        
        Args:
            phone_number (str): Recipient's phone number
            message (str): Message to send
            
        Returns:
            dict: Response from the API
        """
        # Format the phone number
        formatted_number = self.format_phone_number(phone_number)
        print(f"Original: {phone_number} -> Formatted: {formatted_number}")
        
        # URL encode the message
        encoded_message = requests.utils.quote(message)
        
        # Construct the API URL
        url = f"{self.base_url}?recipient={formatted_number}&apikey={self.api_key}&text={encoded_message}"
        
        try:
            # Send the request
            response = requests.get(url)
            
            # Parse response
            if response.status_code == 200:
                result = {
                    'success': True,
                    'status_code': response.status_code,
                    'message': 'SMS sent successfully',
                    'response_text': response.text,
                    'formatted_number': formatted_number
                }
            else:
                result = {
                    'success': False,
                    'status_code': response.status_code,
                    'message': 'Failed to send SMS',
                    'response_text': response.text,
                    'formatted_number': formatted_number
                }
            
            return result
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'message': f'Error occurred: {str(e)}',
                'formatted_number': formatted_number
            }
    
    def send_bulk_sms(self, phone_numbers, message):
        """
        Send SMS to multiple phone numbers
        
        Args:
            phone_numbers (list): List of phone numbers
            message (str): Message to send
            
        Returns:
            list: List of results for each number
        """
        results = []
        for number in phone_numbers:
            result = self.send_sms(number, message)
            results.append(result)
        
        return results


# Example usage
def main():
    # Your API key - replace with your actual key
    API_KEY = "cEngupheojxc"
    
    # Create SMS sender instance
    sms_sender = TextMeBotSMS(API_KEY)
    
    # Test cases for different phone number formats
    test_numbers = [
        "07112167195",  # Standard Kenya mobile format
        "712345678",    # Missing leading 0
        "+254712345678", # Already in +254 format
        "254712345678",  # 254 format without +
        "0112345678",    # Landline (Nairobi)
        "0733 123 456",  # With spaces
        "0733-123-456",  # With dashes
    ]
    
    # Test message
    message = "Hello! This is a test message from TextMeBot API."
    
    # Test single number
    print("=== Testing Single Number ===")
    result = sms_sender.send_sms("07112167195", message)
    print(f"Success: {result['success']}")
    print(f"Response: {result.get('response_text', 'No response')}")
    print(f"Formatted number: {result['formatted_number']}")
    print()
    
    # Test multiple numbers
    print("=== Testing Multiple Numbers ===")
    results = sms_sender.send_bulk_sms(test_numbers[:3], message)
    
    for i, result in enumerate(results):
        print(f"Number {i+1}: {test_numbers[i]}")
        print(f"  Formatted: {result['formatted_number']}")
        print(f"  Success: {result['success']}")
        print(f"  Status: {result.get('status_code', 'N/A')}")
        print()


if __name__ == "__main__":
    # Uncomment the line below to run the example
    # main()
    
    # Simple usage example:
    API_KEY = "cEngupheojxc"
    sms_sender = TextMeBotSMS(API_KEY)
    
    # Send SMS to a number starting with 07
    result = sms_sender.send_sms("0768508448", "This is a test message!")
    
    if result['success']:
        print(f"SMS sent successfully to {result['formatted_number']}")
    else:
        print(f"Failed to send SMS: {result.get('message', 'Unknown error')}")