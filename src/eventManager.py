from typing import ClassVar, Mapping, Sequence, Any, Dict, Optional, Tuple, Final, List, cast

from typing_extensions import Self
from typing import Final

from viam.module.types import Reconfigurable
from viam.proto.app.robot import ModuleConfig
from viam.proto.common import ResourceName, Vector3
from viam.resource.base import ResourceBase
from viam.resource.types import Model, ModelFamily

from viam.services.generic import Generic as GenericService
from viam.components.sensor import Sensor
from viam.utils import SensorReading
from viam.errors import NoCaptureToStoreError
from viam.utils import from_dm_from_extra

from viam.utils import ValueTypes, struct_to_dict
from viam.app.viam_client import ViamClient
from viam.rpc.dial import DialOptions

from . import events, rules, notifications, triggered, actions, globals

import time
import copy
import asyncio
from datetime import datetime, timezone, timedelta
import re
import pydot  # type: ignore
import traceback
# from enum import Enum

# class Modes(Enum):
#     active = "active"
#     inactive = "inactive"

class eventManager(Sensor, Reconfigurable):
    
    MODEL: ClassVar[Model] = Model(ModelFamily("viam", "event-manager"), "eventing")
    
    name: str
    mode: str = "inactive"
    mode_overridden: str = ""
    mode_override_until: Optional[float] = None
    app_client: None
    api_key_id: str
    api_key: str
    part_id: str
    robot_resources: Dict[str, Any] = {}
    dm_sent_status: Dict[str, float] = {}
    event_states: list[events.Event] = []
    stop_events: list[asyncio.Event] = []

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

        attributes = struct_to_dict(config.attributes)

        resources = attributes.get("resources")
        if isinstance(resources, dict):
            for r in resources.keys():
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
        self.name = config.name

        # reset event states
        self.event_states = []

        attributes = struct_to_dict(config.attributes)

        # Set mode directly from attributes
        mode = "inactive"  # Default if not provided
        if attributes.get("mode") and isinstance(attributes.get("mode"), str):
            mode = str(attributes.get("mode"))

        mode_override = attributes.get("mode_override")
        if isinstance(mode_override, dict):
            until_value = mode_override.get("until")
            mode_value = mode_override.get("mode")
            if until_value is not None:
                until = iso8601_to_timestamp(until_value)
                self.mode_override_until = until
                # Store current mode for later
                self.mode_overridden = mode
                if isinstance(mode_value, str):
                    mode = mode_value
        self.mode = mode

        if attributes.get('event_video_capture_padding_secs'):
            self.event_video_capture_padding_secs = attributes.get('event_video_capture_padding_secs')

        dict_events = attributes.get("events")
        if dict_events is not None and isinstance(dict_events, list):
            for e in dict_events:
                if isinstance(e, dict):
                    event = events.Event(**e)
                    event.state = "setup"
                    self.event_states.append(event)

        self.deps = dependencies
        self.robot_resources['resources'] = attributes.get("resources")

        sms_module = config.attributes.fields["sms_module"].string_value or ""
        if sms_module != "":
            self.robot_resources['sms_module_name'] = sms_module
        email_module = config.attributes.fields["email_module"].string_value or ""
        if email_module != "":
            self.robot_resources['email_module_name'] = email_module
        
        self.api_key = config.attributes.fields["app_api_key"].string_value or ''
        self.api_key_id = config.attributes.fields["app_api_key_id"].string_value or ''
        
        while self.stop_events:
            stop_event = self.stop_events.pop()
            stop_event.set()

        asyncio.ensure_future(self.manage_events())
        return
    

    async def viam_connect(self) -> ViamClient:
        dial_options = DialOptions.with_api_key( 
            api_key=self.api_key,
            api_key_id=self.api_key_id
        )
        return await ViamClient.create_from_dial_options(dial_options)
    
    async def manage_events(self):
        self.logger.info("Starting event manager")

        if (self.api_key != '' and self.api_key_id != ''):
            self.app_client = await self.viam_connect()

        event: events.Event
        for event in self.event_states:
            stop_event = asyncio.Event()
            self.stop_events.append(stop_event)
            asyncio.create_task(self.event_check_loop(event, stop_event))
    
    async def event_check_loop(self, event:events.Event, stop_event: asyncio.Event):
        # make the resource logger available globally
        globals.setParam('logger',self.logger)

        # copy so we don't cause locking issue by referencing the same resource across event tasks
        event_resources = copy.deepcopy(self.robot_resources)
        event_resources['_deps'] = self.deps

        if "sms_module_name" in event_resources and event_resources["sms_module_name"] != "":
            actual = event_resources['_deps'][GenericService.get_resource_name(event_resources["sms_module_name"])]
            event_resources['sms_module'] = cast(GenericService, actual)
        if "email_module_name" in event_resources and event_resources["email_module_name"] != "":
            actual = event_resources['_deps'][GenericService.get_resource_name(event_resources["email_module_name"])]
            event_resources['email_module'] = cast(GenericService, actual)

        self.logger.info("Starting event check loop for " + event.name)
        while not stop_event.is_set():
            try:
                if ((self.mode in event.modes) and ((event.is_triggered == False) or ((event.is_triggered == True) and ((time.time() - event.last_triggered) >= event.pause_alerting_on_event_secs)))):
                    start_time = datetime.now()
                    event.state = "monitoring"

                    # reset event and actions before evaluating
                    event.is_triggered = False
                    event.actions_paused = False
                    event.pause_reason = ""

                    event.triggered_camera = ""
                    event.triggered_label = ""
                    event.triggered_rules = {}

                    actions.flip_action_status(event, False)

                    rule_results = []
                    for rule in event.rules:
                        self.logger.debug(rule)
                        result = await rules.eval_rule(rule, event_resources)
                        if result["triggered"] == True:
                            event.sequence_count_current = event.sequence_count_current + 1
                        else:
                            event.sequence_count_current = 0

                        if event.sequence_count_current< event.trigger_sequence_count:
                            # don't consider triggered as we've not met the threshold
                            result["triggered"] = False
                        else:
                            # reset sequence count if we are at the sequence count threshold
                            event.sequence_count_current = 0

                        # rule settings can determine if the event loop should be paused on
                        # non-triggered events
                        if hasattr(rule, 'inverse_pause_secs') and rule.inverse_pause_secs > 0 and not result["triggered"]:
                            event.paused_until = time.time() + rule.inverse_pause_secs
                            event.state = "paused"
                            event.pause_reason = f"{rule.type} rule inverse pause for {rule.inverse_pause_secs} secs"
                            break
                        if hasattr(rule, 'pause_on_known_secs') and rule.pause_on_known_secs > 0 and "known_person_seen" in result and result["known_person_seen"]:
                            event.paused_until = time.time() + rule.pause_on_known_secs
                            event.state = "paused"
                            event.pause_reason = "known person"
                            break                       
                        
                        rule_results.append(result)

                    if (event.state != "paused") and (rules.logical_trigger(event.rule_logic_type, [res['triggered'] for res in rule_results]) == True):
                        event.is_triggered = True
                        event.last_triggered = time.time()
                        event.state = "triggered"

                        rule_index = 0
                        triggered_image = None
                        
                        # not all rules consider or capture images and labels, check if we have them
                        for rule in event.rules:
                            if rule_results[rule_index]['triggered'] == True:
                                if hasattr(rule, 'camera'):
                                    if "value" in rule_results[rule_index]:
                                        event.triggered_label = rule_results[rule_index]["value"]
                                    if "resource" in rule_results[rule_index]:
                                        event.triggered_camera = rule_results[rule_index]["resource"]
                                    if "image" in rule_results[rule_index]:
                                        triggered_image = rule_results[rule_index]["image"]
                                        # remove once copied because we will use rule_results for state reporting
                                        del rule_results[rule_index]["image"]
                                    if event.capture_video:
                                        asyncio.ensure_future(triggered.request_capture(event, event_resources))
                            rule_index = rule_index + 1

                        # Convert list to dictionary with indices as keys
                        event.triggered_rules = {i: result for i, result in enumerate(rule_results)}

                        for n in event.notifications:
                            if triggered_image != None:
                                n.image = triggered_image
                            await notifications.notify(event, n, event_resources)

                    # try to respect detection_hz as desired speed of detections
                    elapsed = (datetime.now() - start_time).total_seconds()
                    to_wait = (1 / event.detection_hz) - elapsed
                    if to_wait > 0:
                        await asyncio.sleep(to_wait)
                elif (event.is_triggered == True) and (event.actions_paused == False):
                    self.logger.debug("checking for ACTIONS")
                    event.state = "actioning"

                    # see if any actions need to be performed
                    sms_message = ""
                    # only poll for SMS if there are actions configured for this event
                    # TODO: only poll if actions are checking for SMS responses
                    if len(event.actions):
                        sms_message = await notifications.check_sms_response(event.notifications, event.last_triggered, event_resources)
                    for action in event.actions:
                        await self.event_action(event, action, sms_message, event_resources)
                    await asyncio.sleep(1)
                else:
                    # sleep if we know we are not currently checking for this event
                    await asyncio.sleep(.5)

                # check if mode override is expired
                if self.mode_overridden != "" and self.mode_override_until is not None and (time.time() >= self.mode_override_until):
                    self.mode = self.mode_overridden
                    self.mode_overridden = ""
                    self.mode_override_until = None
            except Exception as e:
                self.logger.error(f'Error in event check loop: {e}')
                self.logger.error(traceback.format_exc())
                await asyncio.sleep(1)

        self.logger.info("Ending event check loop for " + event.name)
    
    async def event_action(self, event: events.Event, action: actions.Action, message: str, event_resources: Dict[str, Any]):
        should_action = await actions.eval_action(event, action, message)
        if should_action:
            if message != "":
                # once we get a valid message, no other actions should be taken
                event.actions_paused = True
                event.state = "paused"
                event.pause_reason = "sms"
            await actions.do_action(event, action, event_resources)

    async def do_command(
                self,
                command: Mapping[str, ValueTypes],
                *,
                timeout: Optional[float] = None,
                **kwargs
            ) -> Mapping[str, ValueTypes]:
        result: Dict[str, Any] = {}
        for name, args in command.items():
            if name == "get_triggered" and isinstance(args, dict):
                if self.app_client is not None:
                    result["triggered"] = await triggered.get_triggered_cloud(event_manager_name=self.name,organization_id=args.get("organization_id",None), num=args.get("number",5), event_name=args.get("event",None), app_client=self.app_client)
                else:
                    result["triggered"] = []
            elif name == "delete_triggered_video" and isinstance(args, dict):
                if self.app_client is not None:
                    result["total"] = await triggered.delete_from_cloud(id=args.get("id",None), location_id=args.get("location_id",None), organization_id=args.get("organization_id",None), app_client=self.app_client)
                else:
                    result["total"] = 0
            elif name == "trigger_event" and isinstance(args, dict):
                for e in self.event_states:
                    if e.name == args.get("event", ""):
                        e.is_triggered = True
                        e.last_triggered = time.time()
                        e.state = "triggered"
                        result = {"triggered": True}
            elif name == "pause_triggered" and isinstance(args, dict):
                for e in self.event_states:
                    if (e.name == args.get("event", "")) and e.is_triggered == True:
                        e.state = "paused"
                        e.pause_reason = "manual"
                        e.actions_paused = True
                        result = {"paused": True}
            elif name == "respond_triggered" and isinstance(args, dict):
                for e in self.event_states:
                    if (e.name == args.get("event", "")) and e.is_triggered == True:
                        for action in e.actions:
                            await self.event_action(e, action, args.get("response", ""), self.robot_resources)
                result = {"responded": True}

        return result  
    
    async def get_readings(
        self, *, extra: Optional[Mapping[str, Any]] = None, timeout: Optional[float] = None, **kwargs
    ) -> Mapping[str, SensorReading]:
        # No conversion needed since mode is already a string
        ret: Dict[str, Any] = { "state": {}, "mode": self.mode }
        include_dot = False
        graph: pydot.Graph
        if extra is not None and "include_dot" in extra:
            include_dot = extra["include_dot"]
        if include_dot:
            graph = pydot.Dot("my_graph", graph_type="digraph", bgcolor="white", fontname="Courier", fontsize="12pt")

        event_number = 0
        for e in self.event_states:
            # if this is a call from data management, only store events once while they are in 'triggered' or 'actioning' state
            if from_dm_from_extra(dict(extra) if extra is not None else None):
                if (e.state == 'triggered') or (e.state == 'actioning'):
                    if e.name in self.dm_sent_status and self.dm_sent_status[e.name] == e.last_triggered:
                        continue
                    else:
                        self.dm_sent_status[e.name] = e.last_triggered
                else:
                    continue

            ret["state"][e.name] = {
                    "state": e.state,
                }
            
            if e.last_triggered > 0:
                ret["state"][e.name]["last_triggered"] = datetime.fromtimestamp(int(e.last_triggered), timezone.utc).isoformat() + 'Z'
                ret["state"][e.name]["triggered_label"] = e.triggered_label
                ret["state"][e.name]["triggered_camera"] = e.triggered_camera
                
                # Convert triggered_rules from dict with int keys to list for better serialization
                if e.triggered_rules and isinstance(e.triggered_rules, dict):
                    # Sort by numeric keys to maintain order
                    sorted_keys = sorted([k for k in e.triggered_rules.keys() if isinstance(k, int)])
                    ret["state"][e.name]["triggered_rules"] = [e.triggered_rules[k] for k in sorted_keys]
                else:
                    ret["state"][e.name]["triggered_rules"] = []

            if e.pause_reason != "":
                ret["state"][e.name]["pause_reason"] = e.pause_reason

            if include_dot:
                event_number = event_number + 1

                layer = pydot.Subgraph(f'cluster_{event_number}', label=e.name, labelloc="t", style="solid")

                layer.add_node(pydot.Node(f'Setup{event_number}', label="Setup", fontname="Courier", fontsize="10pt", color=layer_color(e.state, "setup")))
                layer.add_node(pydot.Node(f'Monitoring{event_number}', label="Monitoring", fontname="Courier", fontsize="10pt", color=layer_color(e.state, "monitoring")))

                triggered_label = "Triggered"
                if "last_triggered" in ret["state"][e.name]:
                    triggered_label = triggered_label + "\n" + ret["state"][e.name]["last_triggered"]
                    triggered_label = triggered_label + "\n" + ret["state"][e.name]["triggered_label"]
                layer.add_node(pydot.Node(f'Triggered{event_number}', label=triggered_label, fontname="Courier", fontsize="10pt", color=layer_color(e.state, "triggered")))
                
                layer.add_node(pydot.Node(f'Paused{event_number}', label="Paused", fontname="Courier", fontsize="10pt", color=layer_color(e.state, "paused")))

                layer.add_edge(pydot.Edge(f'Setup{event_number}', f'Monitoring{event_number}'))
                layer.add_edge(pydot.Edge(f'Monitoring{event_number}', f'Triggered{event_number}'))
                layer.add_edge(pydot.Edge(f'Paused{event_number}', f'Monitoring{event_number}'))
            
            actions = []
            for a in e.actions:
                a_ret = {
                    "resource": a.resource,
                    "payload": a.payload,
                    "method": a.method,
                    "taken": a.taken,
                    "response_match": a.response_match
                }
                if a.taken:
                    a_ret["when"] = datetime.fromtimestamp(int(a.last_taken), timezone.utc).isoformat() + 'Z'
                actions.append( a_ret )

                if include_dot:
                    a_label = f'Actioning\n{a.resource}/{a.method}'
                    a_font = "Courier"
                    if "when" in a_ret:
                        a_label = a_label + f'\n{a_ret["when"]}'
                        a_font = "Courier bold"
                    action_node= pydot.Node(f'a{event_number}{len(actions)}', label=a_label, fontname=a_font, fontsize="10pt", color=layer_color(e.state, "actioning"))
                    layer.add_node(action_node)
                    layer.add_edge(pydot.Edge(f'Triggered{event_number}', f'a{event_number}{len(actions)}'))
                    layer.add_edge(pydot.Edge(f'a{event_number}{len(actions)}', f'Paused{event_number}'))

            ret["state"][e.name]["actions"] = actions
            if include_dot:
                if len(e.actions) == 0:
                    # connect straight to Paused if no configured actions
                    layer.add_edge(pydot.Edge(f'Triggered{event_number}', f'Paused{event_number}'))

                graph.add_subgraph(layer)

        if from_dm_from_extra(dict(extra) if extra is not None else None) and len(ret["state"]) == 0:
            raise NoCaptureToStoreError()
        
        if include_dot:
            ret["dot"] = graph.to_string()

        return ret
    
def layer_color(state: str, state_node: str) -> str:
    if state == state_node:
        return "red"
    else:
        return "black"

def iso8601_to_timestamp(iso8601_string: str) -> float:
    # Regular expression to match ISO8601 format
    iso8601_regex = r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(\.\d+)?(Z|[+-]\d{2}:?\d{2})?$"
    match = re.match(iso8601_regex, iso8601_string)
    
    if not match:
        raise ValueError("Invalid ISO8601 format")

    year, month, day, hour, minute, second = map(int, match.groups()[:6])
    microsecond = int(float(match.group(7) or '0') * 1000000)
    tz_string = match.group(8)

    if tz_string == 'Z':
        tzinfo = timezone.utc
    elif tz_string:
        # Handle timezone offset
        tz_hours, tz_minutes = map(int, tz_string.replace(':', '')[:-2].split(':'))
        tzinfo = timezone(timedelta(hours=tz_hours, minutes=tz_minutes))
    else:
        tzinfo = None  # Naive datetime

    dt = datetime(year, month, day, hour, minute, second, microsecond, tzinfo=tzinfo)
    
    # Convert to UTC if it's not already
    if dt.tzinfo:
        dt = dt.astimezone(timezone.utc)
    
    # Return Unix timestamp
    return dt.timestamp()