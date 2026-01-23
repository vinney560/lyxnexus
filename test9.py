import requests

url = "https://whatsspot.p.rapidapi.com/message/fast/text"

payload = {
	"message": { "text": "Sending message from WhatsSpot API !!" },
	"numbers": "+254740694312"
}
headers = {
	"x-rapidapi-key": "4406e83311msh635cb32b3525e4bp17f9c1jsn874626c65441",
	"x-rapidapi-host": "whatsspot.p.rapidapi.com",
	"Content-Type": "application/json"
}

response = requests.post(url, json=payload, headers=headers)

print(response.json())