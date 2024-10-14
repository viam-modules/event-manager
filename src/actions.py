import re
import json
import time
from typing import cast

from viam.logging import getLogger
from viam.components.generic import Generic as GenericComponent
from viam.services.generic import Generic as GenericService
from viam.services.vision import VisionClient

from .events import Event
from .actionClass import Action

LOGGER = getLogger(__name__)

def flip_action_status(event:Event, direction:bool):
    action:Action
    for action in event.actions:
        action.taken = direction

async def eval_action(event:Event, action:Action, sms_message):
    if action.taken:
        return False
    if (sms_message != "") and (action.sms_match != ""):
        if re.search(action.sms_match, sms_message):
            LOGGER.debug(f"matched {action.sms_match}")
            return True
    if action.when_secs != -1:
        if (time.time() - event.last_triggered) >= action.when_secs:
            return True
    return False

async def do_action(event:Event, action:Action, resources):
    # certainly this could be improved
    if (resources["resources"][action.resource]["type"] == "component") and (resources["resources"][action.resource]["subtype"] == "generic"):
        resource_dep = resources['_deps'][GenericComponent.get_resource_name(action.resource)]
        resource = cast(GenericComponent, resource_dep)
    if (resources["resources"][action.resource]["type"] == "service") and (resources["resources"][action.resource]["subtype"] == "generic"):
        resource_dep = resources['_deps'][GenericService.get_resource_name(action.resource)]
        resource = cast(GenericService, resource_dep)
    if (resources["resources"][action.resource]["type"] == "service") and (resources["resources"][action.resource]["subtype"] == "vision"):
        resource_dep = resources['_deps'][VisionClient.get_resource_name(action.resource)]
        resource = cast(VisionClient, resource_dep)

    method = getattr(resource, action.method)

    # we don't want to alter action.payload directly as it will be used as a template repeatedly
    payload = action.payload

    # At some point we might want other things to be template variables, for now just label and event name
    payload = payload.replace('<<triggered_label>>', event.triggered_label)
    payload = payload.replace('<<event_name>>', event.name)

    await method(json.loads(payload.replace("'", "\"")))
    action.taken = True
    action.last_taken = time.time()
