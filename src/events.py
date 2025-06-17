from .notificationClass import NotificationEmail, NotificationSMS, NotificationWebhookGET, NotificationPush
from .rules import RuleClassifier, RuleDetector, RuleTracker,RuleTime, RuleCall
from .actionClass import Action

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
    notifications: list[NotificationSMS|NotificationEmail|NotificationWebhookGET|NotificationPush]
    actions: list[Action]
    actions_paused: bool = False
    triggered_rules: dict = {}
    triggered_camera: str = ""
    triggered_label: str = ""
    trigger_sequence_count: int = 1
    sequence_count_current: int = 0
    require_rule_reset: bool = False
    rule_reset_count: int = 1
    rule_reset_counter: int = 0
    backoff_schedule: dict[int, int] = {}  # Maps seconds since first trigger to new pause duration
    backoff_adjustment: int = 0  # Current adjustment to pause_alerting_on_event_secs from backoff schedule
    continuous_trigger_start_time: float = 0  # When the event first started triggering continuously

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
                                self.__dict__[key].append(NotificationSMS(**sms))
                        elif item["type"] == "email":
                            for s in item["to"]:
                                email = {
                                    "preset": item["preset"],
                                    "to": s
                                }
                                self.__dict__[key].append(NotificationEmail(**email))
                        elif item["type"] == "webhook_get":
                            self.__dict__[key].append(NotificationWebhookGET(**item))
                        elif item["type"] == "push":
                            # Assuming fcm_tokens is provided as a list in the config
                            self.__dict__[key].append(NotificationPush(**item))
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
            elif key == "backoff_schedule" and isinstance(value, dict):
                # Convert string keys to integers for backoff schedule
                self.__dict__[key] = {int(k): int(v) for k, v in value.items()}
            else:
                self.__dict__[key] = value

    def get_effective_pause_duration(self) -> int:
        """Get the effective pause duration including any backoff adjustments"""
        return self.pause_alerting_on_event_secs + self.backoff_adjustment

    def _check_backoff_schedule(self, current_time: float) -> None:
        """Check and update backoff adjustment based on time since continuous triggering started"""
        if not self.backoff_schedule or self.continuous_trigger_start_time <= 0:
            self.backoff_adjustment = 0
            return

        # Calculate seconds since continuous triggering started
        seconds_since_start = int(current_time - self.continuous_trigger_start_time)
        
        # Find the applicable backoff threshold
        new_adjustment = 0
        for threshold, adjustment in sorted(self.backoff_schedule.items()):
            if seconds_since_start >= threshold:
                new_adjustment = adjustment - self.pause_alerting_on_event_secs
        
        if new_adjustment != self.backoff_adjustment:
            self.backoff_adjustment = new_adjustment
            try:
                getParam('logger').info(f"Event {self.name} backoff: {seconds_since_start}s since continuous triggering started, adjusting pause by {new_adjustment}s")
            except Exception:
                pass

