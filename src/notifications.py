
import urllib
from PIL import Image
from viam.logging import getLogger

LOGGER = getLogger(__name__)

class NotificationSMS():
    type: str="sms"
    to: str
    preset: str
    image: Image
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            self.__dict__[key] = value

class NotificationEmail():
    type: str="email"
    to: str
    preset: str
    image: Image
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            self.__dict__[key] = value

class NotificationWebhookGET():
    type: str="webhook_get"
    url: str
    image: Image
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            self.__dict__[key] = value

async def notify(event_name:str, notification:NotificationEmail|NotificationSMS|NotificationWebhookGET, resources):

    match notification.type:
        case "email":
            if "email_module" in resources:
                notification_resource = resources['email_module']
            else:
                LOGGER.warning("No email module defined, can't send notification email")
                return
        case "sms":
            if "sms_module" in resources:
                notification_resource = resources['sms_module']
            else:
                LOGGER.warning("No SMS module defined, can't send notification SMS")
                return
        case "webhook_get":
            contents = urllib.request.urlopen(notification.url).read()
            return

    res = await notification_resource.do_command({"command": "send", "to": notification.to, "preset": notification.preset})
    if "error" in res:
        LOGGER.error(f"Error sending {notification.type}: {res["error"]}")
    
    return   