from typing import ClassVar, Mapping, Sequence, Any, Dict, Optional, Tuple, Final, List, cast
from typing_extensions import Self
from typing import Final

from viam.module.types import Reconfigurable
from viam.proto.app.robot import ComponentConfig
from viam.proto.common import ResourceName, Vector3
from viam.resource.base import ResourceBase
from viam.resource.types import Model, ModelFamily
from viam.app.viam_client import ViamClient
from viam.rpc.dial import DialOptions

from viam.components.generic import Generic
from viam.utils import ValueTypes, struct_to_dict

from viam.logging import getLogger

from . import rules
from . import notifications
from . import triggered

import time
import asyncio
import datetime
from enum import Enum

LOGGER = getLogger(__name__)

class Modes(Enum):
    active = 1
    inactive = 2

class Event():
    name: str
    notification_settings: list
    is_triggered: bool = False
    last_triggered: float = 0
    modes: list = ["inactive"]
    rule_logic_type: str = 'AND'
    notifications: list[notifications.NotificationSMS|notifications.NotificationEmail|notifications.NotificationWebhookGET]
    rules: list[rules.RuleDetector|rules.RuleClassifier|rules.RuleTime]

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if isinstance(value, list):
                if key == "notifications":
                    self.__dict__["notifications"] = []
                    for item in value:
                        if item["type"] == "sms":
                            if "sms" in self.notification_settings:
                                for s in self.notification_settings["sms"]:
                                    item.phone = s
                                    self.__dict__[key].append(notifications.NotificationSMS(**item))
                        elif item["type"] == "email":
                            if "email" in self.notification_settings:
                                for e in self.notification_settings["email"]:
                                    item.email = e
                            self.__dict__[key].append(notifications.NotificationEmail(**item))
                        elif item["type"] == "webhook_get":
                            self.__dict__[key].append(notifications.NotificationWebhookGET(**item))
                elif key == "rules":
                    self.__dict__["rules"] = []
                    for item in value:
                        if item["type"] == "detection":
                            self.__dict__[key].append(rules.RuleDetector(**item))
                        elif item["type"] == "classification":
                            self.__dict__[key].append(rules.RuleClassifier(**item))
                        elif item["type"] == "time":
                            self.__dict__[key].append(rules.RuleTime(**item))
                elif key == "modes":
                    self.__dict__["modes"] = []
                    for item in value:
                        self.__dict__[key].append(item)
            else:
                self.__dict__[key] = value

class eventManager(Generic, Reconfigurable):
    
    MODEL: ClassVar[Model] = Model(ModelFamily("viam-soleng", "generic"), "event-manager")
    
    mode: Modes = "inactive"
    pause_alerting_on_event_secs: int = 300
    pause_known_person_secs: int = 3600
    event_video_capture_padding_secs: int = 10
    detection_hz: int = 5
    app_client : None
    api_key_id: str
    api_key: str
    part_id: str
    events = []
    robot_resources = {}
    run_loop = bool = True

    # Constructor
    @classmethod
    def new(cls, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]) -> Self:
        my_class = cls(config.name)
        my_class.reconfigure(config, dependencies)
        return my_class

    # Validates JSON Configuration
    @classmethod
    def validate(cls, config: ComponentConfig):
        deps = []

        camera_config = config.attributes.fields["camera_config"].list_value
        for c in camera_config:
            deps.append(c["video_capture_camera"])
            deps.append(c["vision_service"])
        action_resources = config.attributes.fields["action_resources"].list_value
        for r in action_resources:
            deps.append(r["name"])
        return deps

    # Handles attribute reconfiguration
    def reconfigure(self, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]):
        # setting this to false ensures that if the event loop is currently running, it will stop
        self.run_loop = False

        attributes = struct_to_dict(config.attributes)
        if attributes.get("mode"):
            self.mode = attributes.get("mode")
        else:
            self.mode = 'inactive'

        if attributes.get('pause_known_person_secs'):
            self.pause_known_person_secs = attributes.get('pause_known_person_secs')

        if attributes.get('pause_alerting_on_event_secs'):
            self.pause_known_person_secs = attributes.get('pause_alerting_on_event_secs')

        if attributes.get('event_video_capture_padding_secs'):
            self.pause_known_person_secs = attributes.get('event_video_capture_padding_secs')

        if attributes.get('detection_hz'):
            self.pause_known_person_secs = attributes.get('detection_hz')

        self.events = []
        dict_events = attributes.get("events")
        if dict_events is not None:
            for e in dict_events:
                e.notification_settings = config.attributes.fields["notifications"].list_value
                event = Event(**e)
                self.events.append(event)
        self.robot_resources['_deps'] = dependencies
        self.robot_resources['camera_config'] = attributes.get("camera_config")

        # restart event loop
        self.run_loop = True
        asyncio.ensure_future(self.manage_events())
        return

    async def viam_connect(self) -> ViamClient:
        dial_options = DialOptions.with_api_key( 
            api_key=self.api_key,
            api_key_id=self.api_key_id
        )
        return await ViamClient.create_from_dial_options(dial_options)
    
    async def manage_events(self):
        LOGGER.info("Starting event manager")
        
        event: Event
        for event in self.events:
            asyncio.ensure_future(self.event_check_loop(event))
    
    async def event_check_loop(self, event):
        LOGGER.info("Starting event check loop for " + event.name)
        while self.run_loop:
            if ((self.mode in event.modes) and ((event.is_triggered == False) or ((event.is_triggered == True) and ((time.time() - event.last_triggered) >= self.pause_alerting_on_event_secs)))):
                start_time = datetime.datetime.now()
                # reset trigger before evaluating
                event.is_triggered = False
                rule_results = []
                for rule in event.rules:
                    result = await rules.eval_rule(rule, self.robot_resources)
                    rule_results.append(result)
                if rules.logical_trigger(event.rule_logic_type, rule_results) == True:
                    event.is_triggered = True
                    event.last_triggered = time.time()
                    event_id = str(int(time.time()))
                    # sleep for additional seconds in order to capture more video
                    await asyncio.sleep(self.event_video_capture_padding_secs)
                    rule_index = 0
                    for rule in event.rules:
                        if rule_results[rule_index]['triggered'] == True and hasattr(rule, 'cameras'):
                            for c in rule.cameras:
                                stored_filename = await triggered.request_capture(c, self.event_video_capture_padding_secs, self.robot_resources)
                                # TODO - track filename for notification response handling
                        rule_index = rule_index + 1
                    for n in event.notifications:
                        LOGGER.info(n.type)
                        notifications.notify(event.name, n)

                # try to respect detection_hz as desired speed of detections
                elapsed = (datetime.datetime.now() - start_time).total_seconds()
                to_wait = (1 / self.detection_hz) - elapsed
                if to_wait > 0:
                    await asyncio.sleep(to_wait)
            else:
                # sleep for a bit longer if we know we are not currently checking for this event
                await asyncio.sleep(.5)
    
    async def do_command(
                self,
                command: Mapping[str, ValueTypes],
                *,
                timeout: Optional[float] = None,
                **kwargs
            ) -> Mapping[str, ValueTypes]:
        result = {}
        for name, args in command.items():
            if name == "get_triggered":
                result["triggered"] = await triggered.get_triggered_cloud(num=args.get("number",5), camera=args.get("camera",None), event=args.get("event",None), app_client=self.app_client)
            elif name == "clear_triggered":
                result["total"] = await triggered.delete_from_cloud(camera=args.get("camera",None), event=args.get("event",None), id=args.get("id",None), app_client=self.app_client)
        return result  