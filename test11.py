import requests

url = "https://mywhinlite.p.rapidapi.com/sendmsg"

payload = {
    "phone_number_or_group_id": "254740694312",  # Replace with actual number
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
    response.raise_for_status()  # Raise an exception for bad status codes
    print("Success!")
    print(response.json())
except requests.exceptions.ConnectionError as e:
    print(f"Connection error: {e}")
    print("This is likely still a DNS/network issue. Check your DNS configuration.")
except requests.exceptions.HTTPError as e:
    print(f"HTTP error: {e}")
    print("This might be an issue with your API key or the phone number format.")
except Exception as e:
    print(f"Unexpected error: {e}")