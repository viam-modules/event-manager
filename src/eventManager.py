from typing import ClassVar, Mapping, Sequence, Any, Dict, Optional, Tuple, Final, List, cast
from typing_extensions import Self
from typing import Final

from viam.module.types import Reconfigurable
from viam.proto.app.robot import ModuleConfig
from viam.proto.common import ResourceName, Vector3
from viam.resource.base import ResourceBase
from viam.resource.types import Model, ModelFamily
from viam.services.generic import Generic as GenericService
from viam.utils import ValueTypes, struct_to_dict
from viam.app.viam_client import ViamClient
from viam.rpc.dial import DialOptions

from viam.logging import getLogger

from . import rules
from . import notifications
from . import triggered
from . import actions

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
    rules: list[rules.RuleDetector|rules.RuleClassifier|rules.RuleTime]
    notifications: list[notifications.NotificationSMS|notifications.NotificationEmail|notifications.NotificationWebhookGET]
    actions: list[actions.Action]
    actions_paused: bool = False

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
                            if "sms" in notification_settings:
                                for s in notification_settings["sms"]:
                                    item['to'] = s
                                    self.__dict__[key].append(notifications.NotificationSMS(**item))
                        elif item["type"] == "email":
                            if "email" in notification_settings:
                                for e in notification_settings["email"]:
                                    item['to'] = e
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
                        elif item["type"] == "tracker":
                            self.__dict__[key].append(rules.RuleTracker(**item))
                elif key == "modes":
                    self.__dict__["modes"] = []
                    for item in value:
                        self.__dict__[key].append(item)
                elif key == "actions":
                    for item in value:
                        self.__dict__[key].append(actions.Action(**item))
            else:
                self.__dict__[key] = value

class eventManager(GenericService, Reconfigurable):
    
    MODEL: ClassVar[Model] = Model(ModelFamily("viam-soleng", "generic"), "event-manager")
    
    mode: Modes = "inactive"
    pause_alerting_on_event_secs: int = 300
    pause_known_person_secs: int = 120
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
    def new(cls, config: ModuleConfig, dependencies: Mapping[ResourceName, ResourceBase]) -> Self:
        my_class = cls(config.name)
        my_class.reconfigure(config, dependencies)
        return my_class

    # Validates JSON Configuration
    @classmethod
    def validate(cls, config: ModuleConfig):
        deps = []

        api_key = config.attributes.fields["app_api_key"].string_value or ''
        if api_key == '':
            raise Exception("An app_api_key must be defined")

        api_key_id = config.attributes.fields["app_api_key_id"].string_value or ''
        if api_key_id == '':
            raise Exception("An app_api_key_id must be defined")
        
        attributes = struct_to_dict(config.attributes)
        camera_config = attributes.get("camera_config")
        for c in camera_config:
            deps.append(camera_config[c]["video_capture_camera"])
            deps.append(camera_config[c]["vision_service"])
        action_resources = attributes.get("action_resources")
        for r in action_resources.keys():
            deps.append(r)
        sms_module = config.attributes.fields["sms_module"].string_value or ""
        if sms_module != "":
            deps.append(sms_module)
        email_module = config.attributes.fields["email_module"].string_value or ""
        if email_module != "":
            deps.append(email_module)
        return deps

    # Handles attribute reconfiguration
    def reconfigure(self, config: ModuleConfig, dependencies: Mapping[ResourceName, ResourceBase]):
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
            self.pause_alerting_on_event_secs = attributes.get('pause_alerting_on_event_secs')

        if attributes.get('event_video_capture_padding_secs'):
            self.event_video_capture_padding_secs = attributes.get('event_video_capture_padding_secs')

        if attributes.get('detection_hz'):
            self.detection_hz = attributes.get('detection_hz')

        self.events = []
        dict_events = attributes.get("events")
        if dict_events is not None:
            for e in dict_events:
                e['notification_settings'] = attributes.get('notifications')
                event = Event(**e)
                self.events.append(event)

        self.robot_resources['_deps'] = dependencies
        self.robot_resources['camera_config'] = attributes.get("camera_config")
        self.robot_resources['action_resources'] = attributes.get("action_resources")

        sms_module = config.attributes.fields["sms_module"].string_value or ""
        if sms_module != "":
            actual = dependencies[GenericService.get_resource_name(sms_module)]
            self.robot_resources['sms_module'] = cast(GenericService, actual)
        email_module = config.attributes.fields["email_module"].string_value or ""
        if email_module != "":
            actual = dependencies[GenericService.get_resource_name(email_module)]
            self.robot_resources['email_module'] = cast(GenericService, actual)
        
        self.api_key = config.attributes.fields["app_api_key"].string_value or ''
        self.api_key_id = config.attributes.fields["app_api_key_id"].string_value or ''
        
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
        
        self.app_client = await self.viam_connect()

        event: Event
        for event in self.events:
            await asyncio.ensure_future(self.event_check_loop(event))
    
    async def event_check_loop(self, event:Event):
        LOGGER.info("Starting event check loop for " + event.name)
        while self.run_loop:
            if ((self.mode in event.modes) and ((event.is_triggered == False) or ((event.is_triggered == True) and ((time.time() - event.last_triggered) >= self.pause_alerting_on_event_secs)))):
                start_time = datetime.datetime.now()
                # reset trigger and actions before evaluating
                event.is_triggered = False
                actions.flip_action_status(event, False)
                event.actions_paused = False

                rule_results = []
                for rule in event.rules:
                    result = await rules.eval_rule(rule, self.robot_resources)
                    rule_results.append(result)

                if rules.logical_trigger(event.rule_logic_type, [res['triggered'] for res in rule_results]) == True:
                    event.is_triggered = True
                    event.last_triggered = time.time()
                    rule_index = 0
                    triggered_image = None
                    for rule in event.rules:
                        if rule_results[rule_index]['triggered'] == True and hasattr(rule, 'cameras'):
                            if "image" in rule_results[rule_index]:
                                triggered_image = rule_results[rule_index]["image"]
                            for c in rule.cameras:
                                asyncio.ensure_future(triggered.request_capture(c, event.name, self.event_video_capture_padding_secs, self.robot_resources))
                        rule_index = rule_index + 1
                    for n in event.notifications:
                        if triggered_image != None:
                            n.image = triggered_image
                        await notifications.notify(event.name, n, self.robot_resources)

                # try to respect detection_hz as desired speed of detections
                elapsed = (datetime.datetime.now() - start_time).total_seconds()
                to_wait = (1 / self.detection_hz) - elapsed
                if to_wait > 0:
                    await asyncio.sleep(to_wait)
            elif (event.is_triggered == True) and (event.actions_paused == False):
                LOGGER.error("checking for ACTIONS")
                # see if any actions need to be performed
                sms_message = await notifications.check_sms_response(event.notifications, event.last_triggered, self.robot_resources)
                for action in event.actions:
                    should_action = await actions.eval_action(event, action, sms_message)
                    if should_action:
                        if sms_message != "":
                            # once we get a valid SMS message, no other actions should be taken
                            event.actions_paused = True
                        await actions.do_action(event, action, self.robot_resources)
                await asyncio.sleep(.5)
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
            elif name == "delete_triggered":
                result["total"] = await triggered.delete_from_cloud(id=args.get("id",None), location_id=args.get("location_id",None), organization_id=args.get("organization_id",None), app_client=self.app_client)
        return result  