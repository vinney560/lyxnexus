import requests
URL = 'https://lyxnexus.onrender.com/main-page'
response = requests.get(URL)
if response.status_code == 200:
    print("Successfully accessed the main page!")
    print(response.text)
else:
    print(f"Failed to access the main page. Status code: {response.status_code}")