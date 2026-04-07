
import africastalking
from django.conf import settings

africastalking.initialize(
    username=settings.AFRICASTALKING_USERNAME,
    api_key=settings.AFRICASTALKING_API_KEY
)
sms = africastalking.SMS

def send_sms(phone, message):
    try:
        response = sms.send(message,[phone])
        return response
    except Exception as e:
        return {"error":str(e)}
    