import requests
from bs4 import BeautifulSoup
URL = 'https://lyxnexus.onrender.com/main-page'
response = requests.get(URL)
if response.status_code == 200:
    print("Successfully accessed the main page!")
    soup = BeautifulSoup(response.text, 'html.parser')
    print("\nPRETTY HTML TITLE:")
    print(soup.title.string if soup.title else "No title found")
else:
    print(f"Failed to access the main page. Status code: {response.status_code}")