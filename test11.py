import requests

url = "https://mywhinlite.p.rapidapi.com/sendmsg"

payload = {
    "phone_number_or_group_id": "254740694312",  
    "is_group": False,
    "message": "Hello! This API works too! https://rapidapi.com/inutil-inutil-default/api/mywhinlite"
}
headers = {
    "x-rapidapi-key": "e58f612ademsh7e87404e0c73949p1409e8jsnc030330352f6",
    "x-rapidapi-host": "mywhinlite.p.rapidapi.com",
    "Content-Type": "application/json"
}

try:
    response = requests.post(url, json=payload, headers=headers)
    
    # Debug information
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"Raw Response Text: {response.text}")
    
    # Try to parse JSON
    print("\nAttempting to parse JSON:")
    print(response.json())
    
except requests.exceptions.RequestException as e:
    print(f"Request Error: {e}")
except ValueError as e:
    print(f"JSON Parse Error: {e}")