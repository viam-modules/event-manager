import re
import json
from typing import cast

from viam.logging import getLogger
from viam.components.generic import Generic as GenericComponent
from viam.services.generic import Generic as GenericService
from viam.services.vision import VisionClient

LOGGER = getLogger(__name__)

class Action():
    resource: str
    method: str
    payload: str
    when_secs: int
    sms_match: str = ""
    taken: bool = False
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            self.__dict__[key] = value

def flip_action_status(event, direction:bool):
    action:Action
    for action in event.actions:
        action.taken = direction

async def eval_action(event, action:Action, sms_message):
    if (sms_message != "") and (action.sms_match != ""):
        if re.search(action.sms_match, sms_message):
            LOGGER.error(f"matched {action.sms_match}")
            return True
    return False

async def do_action(event, action:Action, resources):
    # certainly this could be improved
    if (resources["action_resources"][action.resource]["type"] == "component") and (resources["action_resources"][action.resource]["subtype"] == "generic"):
        resource_dep = resources['_deps'][GenericComponent.get_resource_name(action.resource)]
        resource = cast(GenericComponent, resource_dep)
    if (resources["action_resources"][action.resource]["type"] == "service") and (resources["action_resources"][action.resource]["subtype"] == "generic"):
        resource_dep = resources['_deps'][GenericService.get_resource_name(action.resource)]
        resource = cast(GenericService, resource_dep)
    if (resources["action_resources"][action.resource]["type"] == "service") and (resources["action_resources"][action.resource]["subtype"] == "vision"):
        resource_dep = resources['_deps'][VisionClient.get_resource_name(action.resource)]
        resource = cast(VisionClient, resource_dep)

    method = getattr(resource, action.method)

    # TODO: allow for string replacement in payload for things like label
    await method(json.loads(action.payload.replace("'", "\"")))
    action.taken = True