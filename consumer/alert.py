from twilio.rest import Client
import os

account_sid = os.getenv('TWILIO_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
messaging_service_sid = os.getenv('TWILIO_MSG_SVC_SID')
phone_number = os.getenv('PTN')
client = Client(account_sid, auth_token)

def alert(value, location):
  message = client.messages.create(
    messaging_service_sid=messaging_service_sid,
    body=f'Hello, the current AQI is {value} at {location}.',
    to=phone_number
  )
  
  return message
