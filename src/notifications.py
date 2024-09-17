
import urllib
from PIL import Image
from viam.logging import getLogger
import base64
from io import BytesIO

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
                LOGGER.warn("No email module defined, can't send notification email")
                return
        case "sms":
            if "sms_module" in resources:
                notification_resource = resources['sms_module']
            else:
                LOGGER.warn("No SMS module defined, can't send notification SMS")
                return
        case "webhook_get":
            contents = urllib.request.urlopen(notification.url).read()
            return

    notification_args = {"command": "send", "to": notification.to, "preset": notification.preset}
    
    buffered = BytesIO()
    notification.image.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode("ascii")
    notification_args["media_base64"] = img_str
    notification_args["media_mime_type"] =  "image/jpeg"

    res = await notification_resource.do_command(notification_args)
    if "error" in res:
        LOGGER.error(f"Error sending {notification.type}: {res["error"]}")
    
    return   