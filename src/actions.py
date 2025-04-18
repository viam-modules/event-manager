import re
import time
from typing import Dict, Any

from .globals import getParam
from .events import Event
from .actionClass import Action
from .resourceUtils import call_method

def flip_action_status(event:Event, direction:bool):
    action:Action
    for action in event.actions:
        action.taken = direction

async def eval_action(event:Event, action:Action, sms_message: str):
    if action.taken:
        return False
    if (sms_message != "") and (action.response_match != ""):
        if re.search(action.response_match, sms_message):
            getParam('logger').debug(f"matched {action.response_match}")
            return True
    if action.when_secs != -1:
        if (time.time() - event.last_triggered) >= action.when_secs:
            return True
    return False

async def do_action(event:Event, action:Action, resources: Dict[str, Any]):
    await call_method(resources, action.resource, action.method, action.payload, event)

    action.taken = True
    action.last_taken = int(time.time())
