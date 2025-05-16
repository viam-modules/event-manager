from PIL import Image
from typing import Any, Optional

class NotificationSMS():
    type: str="sms"
    to: str
    preset: str
    image: Optional[Image.Image] = None
    include_image: bool = True
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            self.__dict__[key] = value

class NotificationEmail():
    type: str="email"
    to: str
    preset: str
    image: Optional[Image.Image] = None
    include_image: bool = False
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            self.__dict__[key] = value

class NotificationWebhookGET():
    type: str="webhook_get"
    url: str
    image: Optional[Image.Image] = None
    include_image: bool = False
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            self.__dict__[key] = value

class NotificationPush():
    type: str="push"
    fcm_tokens: list[str]
    preset: str
    image: Optional[Image.Image] = None
    include_image: bool = False
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            self.__dict__[key] = value