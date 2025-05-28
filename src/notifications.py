import urllib.request
import base64
from io import BytesIO
from datetime import datetime, timezone
from typing import Dict, Any, List, Union, Optional
from PIL import Image
from . import events
from .notificationClass import NotificationEmail, NotificationSMS, NotificationWebhookGET, NotificationPush
from .globals import getParam


async def notify(event: events.Event, notification: Union[NotificationEmail, NotificationSMS, NotificationWebhookGET, NotificationPush], resources: Dict[str, Any]) -> None:

    notification_args: Dict[str, Any] = {"command": "send", "preset": notification.preset if hasattr(notification, "preset") else None, 
                            "template_vars": {
                                "event_name": event.name, 
                                "triggered_label": event.triggered_label, 
                                "triggered_camera": event.triggered_camera
                            }}
    
    # Add 'to' field only if it exists in the notification object
    if hasattr(notification, "to"):
        notification_args["to"] = notification.to
    # Add 'fcm_tokens' field only if it exists in the notification object
    if hasattr(notification, "fcm_tokens"):
        notification_args["fcm_tokens"] = notification.fcm_tokens

    # create base64 representation of the image if needed
    if hasattr(notification, "include_image") and notification.include_image and notification.image is not None:
        buffered = BytesIO()
        notification.image.save(buffered, format="JPEG")
        img_base64_str = base64.b64encode(buffered.getvalue()).decode("ascii")
    
    match notification.type:
        case "email":
            if "email_module" in resources:
                notification_resource = resources['email_module']
                if hasattr(notification, "include_image") and notification.include_image:
                    if 'img_base64_str' in locals():
                        notification_args["template_vars"]["image_base64"] = img_base64_str
                        notification_args["template_vars"]["media_mime_type"] = "image/jpeg"
            else:
                getParam('logger').warning("No email module defined, can't send notification email")
                return
        case "sms":
            if "sms_module" in resources:
                notification_resource = resources['sms_module']
                if hasattr(notification, "include_image") and notification.include_image:
                    # Only add media_base64 if img_base64_str was created
                    if 'img_base64_str' in locals():
                        notification_args["media_base64"] = img_base64_str
                        notification_args["media_mime_type"] = "image/jpeg"
            else:
                getParam('logger').warning("No SMS module defined, can't send notification SMS")
                return
        case "webhook_get":
            if isinstance(notification, NotificationWebhookGET) and hasattr(notification, "url"):
                contents = urllib.request.urlopen(notification.url).read()
            return
        case "push":
            if "push_module" in resources:
                notification_resource = resources['push_module']
                if hasattr(notification, "include_image") and notification.include_image:
                    if 'img_base64_str' in locals():
                        notification_args["media_base64"] = img_base64_str
                        notification_args["media_mime_type"] = "image/jpeg"
                        notification_args["data"] = {
                            "type": "camera_event",
                            "cameraName": event.triggered_camera
                        }
            else:
                getParam('logger').warning("No push module defined, can't send push notification")
                return
    
    try:
        res = await notification_resource.do_command(notification_args)
        if "error" in res:
            getParam('logger').error(f"Error sending {notification.type}: {res['error']}")
    except Exception as e:
        getParam('logger').error(f'Unexpected error, notification not sent {e}')
        
    return   

async def check_sms_response(notifications: List[Union[NotificationEmail, NotificationSMS, NotificationWebhookGET, NotificationPush]], since: float, resources: Dict[str, Any]) -> str:
    formatted_time = datetime.fromtimestamp(since, timezone.utc).strftime('%d/%m/%Y %H:%M:%S')
    for n in notifications:
        if n.type == "sms" and hasattr(n, "to"):
            sms_args: Dict[str, Any] = { "command": "get", "number": 1, "from": n.to, "time_start": formatted_time }
            getParam('logger').debug(sms_args)
            res = await resources['sms_module'].do_command(sms_args)
            if len(res["messages"]):
                getParam('logger').debug(res)
                return res["messages"][0]["body"]
    return ""