import asyncio
from notificationapi_python_server_sdk import notificationapi

notificationapi.init(
  "tn46tvp8r580do0ei9jujqhe75", # Client ID
  "taf382qxy2x7yt2270q1gnf7kurz1pjkxgwmf8lntt3qjww2cvsvz536gv"# Client Secret
)

async def send_notification():
    response = await notificationapi.send({
      "type": "announce_2",
      "to": {
         "id": "vincentkipngetich479@gmail.com",
         "number": "+254740694312" # Replace with your phone number, use format [+][country code][area code][local number]
      },
        "sms": {
            "message": "Hello, world!"
        }
    })
    
asyncio.run(send_notification())