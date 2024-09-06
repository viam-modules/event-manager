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
from enum import Enum

LOGGER = getLogger(__name__)

class Modes(Enum):
    home = 1
    away = 2

class Event():
    name: str
    is_triggered: bool = False
    last_triggered: float = 0
    modes: list = ["home"]
    debounce_interval_secs: int = 300
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
                            self.__dict__[key].append(notifications.NotificationSMS(**item))
                        elif item["type"] == "email":
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
    
    mode: Modes = "home"
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
        return

    # Handles attribute reconfiguration
    def reconfigure(self, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]):
        self.run_loop = False

        self.api_key = config.attributes.fields["app_api_key"].string_value or ''
        self.api_key_id = config.attributes.fields["app_api_key_id"].string_value or ''
        self.part_id = config.attributes.fields["part_id"].string_value or ''

        attributes = struct_to_dict(config.attributes)
        if attributes.get("mode"):
            self.mode = attributes.get("mode")
        else:
            self.mode = 'home'

        self.events = []
        dict_events = attributes.get("events")
        if dict_events is not None:
            for e in dict_events:
                event = Event(**e)
                self.events.append(event)
        self.robot_resources['_deps'] = dependencies
        self.robot_resources['buffers'] = {}
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
        LOGGER.info("Starting SAVCAM event loop")
        
        if self.use_data_management:
            self.app_client = await self.viam_connect()
        
        while self.run_loop:
            event: Event
            for event in self.events:
                if ((self.mode in event.modes) and ((event.is_triggered == False) or ((event.is_triggered == True) and ((time.time() - event.last_triggered) >= event.debounce_interval_secs)))):
                    # reset trigger before evaluating
                    event.is_triggered = False
                    rule_results = []
                    for rule in event.rules:
                        result = await rules.eval_rule(rule, event.name, self.robot_resources)
                        rule_results.append(result)
                    if rules.logical_trigger(event.rule_logic_type, rule_results) == True:
                        event.is_triggered = True
                        event.last_triggered = time.time()
                        event_id = str(int(time.time()))
                        # sleep for a second in order to capture a bit more images
                        await asyncio.sleep(1)
                        # write image sequences leading up to event
                        rule_index = 0
                        for rule in event.rules:
                            if rule_results[rule_index] == True and hasattr(rule, 'cameras'):
                                for c in rule.cameras:
                                    out_dir = triggered.copy_image_sequence(c, event.name, event_id)
                                    if self.use_data_management:
                                        await triggered.send_data(c, event.name, event_id, self.app_client, self.part_id, out_dir)
                            rule_index = rule_index + 1
                        for n in event.notifications:
                            LOGGER.info(n.type)
                            notifications.notify(event.name, n)
                    await asyncio.sleep(.05)
                else:
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