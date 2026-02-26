import requests

api_key = "774660F4-D219-483F-A251-08EAFE2B5346"
phone = "254740694312"  # Replace with actual number
message = "Hello!"

# Try these different URL formats
urls = [
    f"https://appslink.io/api/send?apikey={api_key}&number={phone}&message={message}",
    f"https://appslink.io/send?api_key={api_key}&to={phone}&text={message}",
    f"https://api.appslink.io/v1/messages?key={api_key}&phone={phone}&msg={message}"
]

for url in urls:
    print(f"Trying: {url}")
    response = requests.get(url)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    print("-" * 50)