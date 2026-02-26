import requests
import os

API_KEY = "774660F4-D219-483F-A251-08EAFE2B5346"
API_URL = 'https://app.appslink.io/instances/87c9ed9d-fa3d-45fa-8b86-0a32e38e1435'

payload = {
    "to": "+254740694312",
    "type": "text",
    "text": {"body": "Hello from AppsLink.io!"}
}

response = requests.get(API_URL, json=payload, headers={
    'Authorization': f'Bearer {API_KEY}',
    'Content-Type': 'application/json'
})

if response.ok:
    print("Message sent:", response.text)
else:
    print(f"Error {response.status_code}: {response.text}")