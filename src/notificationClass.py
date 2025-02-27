from PIL import Image

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
    include_image: bool = False
    
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