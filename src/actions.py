import re
import time

from viam.logging import getLogger

from .events import Event
from .actionClass import Action
from .resourceUtils import call_method

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
    await call_method(resources, action.resource, action.method, action.payload, event)

    action.taken = True
    action.last_taken = time.time()
