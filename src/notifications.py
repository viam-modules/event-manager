import urllib.request

from email.mime.text import MIMEText
from subprocess import Popen, PIPE
from viam.logging import getLogger

LOGGER = getLogger(__name__)

# att|verizon|sprint|tmobile|boost|metropcs
carrier_email_gateways = {
    "att": "mms.att.net",
    "verizon": "vzwpix.com",
    "sprint": "pm.sprint.com",
    "tmobile": "tmomail.net",
    "boost": "myboostmobile.com",
    "metropcs": "mymetropcs.com"
}

class NotificationSMS():
    type: str="sms"
    url: str
    carrier: str
    phone: str
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            self.__dict__[key] = value

class NotificationEmail():
    type: str="email"
    address: str
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            self.__dict__[key] = value

class NotificationWebhookGET():
    type: str="webhook_get"
    url: str
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            self.__dict__[key] = value

def notify(event_name:str, notification:NotificationEmail|NotificationSMS|NotificationWebhookGET):

    match notification.type:
        case "email":
            send_email(event_name, notification, False)
        case "sms":
            send_email(event_name, notification, True)
        case "webhook_get":
            contents = urllib.request.urlopen(notification.url).read()

    return


def send_email(event_name:str, notification:NotificationEmail|NotificationSMS, is_sms:bool):
    msg = MIMEText("Event triggered!")
    if is_sms:
        to_address = notification.phone + "@" + carrier_email_gateways[notification.carrier]
    else:
        to_address = notification.address
    msg['To'] = to_address
    msg['Subject'] = "SAVCAM event: " + event_name

    try:
        p = Popen(["/usr/sbin/sendmail", "-t", "-oi"], stdin=PIPE, universal_newlines=True)
        p.communicate(msg.as_string())
    except Exception as e:
        LOGGER.error(e.output)        