import requests
from bs4 import BeautifulSoup

response = requests.get('https://lyxnexus.onrender.com/admin')
soup = BeautifulSoup(response.content, 'html.parser')

title = soup.find_all("title")[0].text
print(f'Title of the page: {title}')