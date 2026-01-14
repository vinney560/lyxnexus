import requests

url = "https://whatsapp-messaging-hub.p.rapidapi.com/WhatsappSendMessage"

payload = {
	"token": "ZJszbHhdC1lfa7SisNDc40vd8euuScazWtIdKoLr4Nd98LDWtPzN6clxZ2VMdBae",
	"phone_number_or_group_id": "254740694312",
	"is_group": False,
	"message": "Hello! This API really works! https://rapidapi.com/finestoreuk/api/whatsapp-messaging-hub",
	"quoted_message_id": "",
	"quoted_phone_number": "",
	"reply_privately": False,
	"reply_privately_group_id": ""
}
headers = {
	"x-rapidapi-key": "4406e83311msh635cb32b3525e4bp17f9c1jsn874626c65441",
	"x-rapidapi-host": "whatsapp-messaging-hub.p.rapidapi.com",
	"Content-Type": "application/json"
}

response = requests.post(url, json=payload, headers=headers)

print(response.json())