from twilio.rest import Client
import os

account_sid = os.getenv('TWILIO_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
phone_number = os.getenv('PTN')
client = Client(account_sid, auth_token)

def alert(value, location):
  message = client.messages.create(
    from_='+12766001085',
    body=f'Hello, the current AQI is {value} at the {location} location.',
    to=phone_number)
  return message

