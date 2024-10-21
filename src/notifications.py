import urllib
from PIL import Image
from viam.logging import getLogger
import base64
from io import BytesIO
from datetime import datetime, timezone

LOGGER = getLogger(__name__)

class NotificationSMS():
    type: str="sms"
    to: str
    preset: str
    image: Image
    include_image: bool = True
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

    notification_args = {"command": "send", "to": notification.to, "preset": notification.preset}
    
    if notification.include_image:
        buffered = BytesIO()
        notification.image.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode("ascii")
        notification_args["media_base64"] = img_str
        notification_args["media_mime_type"] =  "image/jpeg"

    try:
        res = await notification_resource.do_command(notification_args)
        if "error" in res:
            LOGGER.error(f"Error sending {notification.type}: {res["error"]}")
    except Exception as e:
        LOGGER.error(f'Unexpected error, notification not sent {e}')
        
    return   

async def check_sms_response(notifications:list[NotificationEmail|NotificationSMS|NotificationWebhookGET], since, resources):
    formatted_time = datetime.fromtimestamp(since, timezone.utc).strftime('%d/%m/%Y %H:%M:%S')
    for n in notifications:
        if n.type == "sms":
            sms_args = { "command": "get", "number": 1, "from": n.to, "time_start": formatted_time }
            LOGGER.debug(sms_args)
            res = await resources['sms_module'].do_command(sms_args)
            if len(res["messages"]):
                LOGGER.debug(res)
                return res["messages"][0]["body"]
    return ""