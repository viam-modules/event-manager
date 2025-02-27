from . import notifications
from .rules import RuleClassifier, RuleDetector, RuleTracker,RuleTime, RuleCall
from .actionClass import Action

from viam.logging import getLogger
LOGGER = getLogger(__name__)

class Event():
    name: str
    state: str = 'paused'
    capture_video: bool = False
    video_capture_resource: str
    event_video_capture_padding_secs: int = 10
    pause_alerting_on_event_secs: int = 300
    detection_hz: int = 5
    notification_settings: list
    is_triggered: bool = False
    last_triggered: float = 0
    paused_until: float = 0
    pause_reason: str = ""
    modes: list = ["inactive"]
    rule_logic_type: str = 'AND'
    rules: list[RuleDetector|RuleClassifier|RuleTime|RuleTracker|RuleCall]
    notifications: list[notifications.NotificationSMS|notifications.NotificationEmail|notifications.NotificationWebhookGET]
    actions: list[Action]
    actions_paused: bool = False
    triggered_value = ""
    triggered_resource: str = ""
    trigger_sequence_count: int = 1
    sequence_count_current: int = 0

    def __init__(self, **kwargs):
        notification_settings = kwargs.get('notification_settings')
        
        # these are optional
        self.__dict__["actions"] = []
        self.__dict__["notifications"] = []

        for key, value in kwargs.items():
            if isinstance(value, list):
                if key == "notifications":
                    for item in value:
                        if item["type"] == "sms":
                            for s in item["to"]:
                                sms = {
                                    "preset": item["preset"],
                                    "to": s
                                }
                                self.__dict__[key].append(notifications.NotificationSMS(**sms))
                        elif item["type"] == "email":
                            for s in item["to"]:
                                email = {
                                    "preset": item["preset"],
                                    "to": s
                                }
                                self.__dict__[key].append(notifications.NotificationEmail(**email))
                        elif item["type"] == "webhook_get":
                            self.__dict__[key].append(notifications.NotificationWebhookGET(**item))
                elif key == "rules":
                    self.__dict__["rules"] = []
                    for item in value:
                        if item["type"] == "detection":
                            self.__dict__[key].append(RuleDetector(**item))
                        elif item["type"] == "classification":
                            self.__dict__[key].append(RuleClassifier(**item))
                        elif item["type"] == "time":
                            self.__dict__[key].append(RuleTime(**item))
                        elif item["type"] == "tracker":
                            self.__dict__[key].append(RuleTracker(**item))
                        elif item["type"] == "call":
                            self.__dict__[key].append(RuleCall(**item))
                elif key == "modes":
                    self.__dict__["modes"] = []
                    for item in value:
                        self.__dict__[key].append(item)
                elif key == "actions":
                    for item in value:
                        self.__dict__[key].append(Action(**item))
            else:
                self.__dict__[key] = value

