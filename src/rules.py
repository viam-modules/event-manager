import re
import asyncio

from datetime import datetime
from typing import cast
from PIL import Image
from . import logic
from .resourceUtils import call_method

from viam.services.vision import VisionClient, Detection, Classification, Vision
from viam.logging import getLogger
from viam.media.utils.pil import viam_to_pil_image

LOGGER = getLogger(__name__)

class TimeRange():
    start_hour: int
    end_hour: int
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            self.__dict__[key] = value

class RuleDetector():
    type: str="detection"
    camera: str
    detector: str
    class_regex: str
    confidence_pct: float
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            self.__dict__[key] = value
class RuleClassifier():
    type: str="classification"
    camera: str
    classifier: str
    class_regex: str
    confidence_pct: float
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            self.__dict__[key] = value

class RuleTracker():
    type: str="tracker"
    camera: str
    tracker: str
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            self.__dict__[key] = value

class RuleCall():
    type: str="call"
    resource: str
    method: str
    payload:str = ""
    result_path: str = ""
    result_function: str = ""
    result_operator: str
    result_value: any
    inverse_pause_secs: int

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            self.__dict__[key] = value
class RuleTime():
    type: str="time"
    ranges: list[TimeRange]
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if isinstance(value, list):
                self.__dict__[key] = []
                for item in value:
                     self.__dict__[key].append(TimeRange(**item))
            else:
                self.__dict__[key] = value

async def eval_rule(rule:RuleTime|RuleDetector|RuleClassifier|RuleTracker|RuleCall, resources):
    response = { "triggered" : False, "image": None, "label": None }
    match rule.type:
        case "time":
            curr_time = datetime.now()
            for r in rule.ranges:
                if (curr_time.hour >= r.start_hour) and (curr_time.hour < r.end_hour):
                    LOGGER.debug("Time triggered")
                    response["triggered"] = True   
        case "detection":
            detector = _get_vision_service(rule.detector, resources)
            all = await detector.capture_all_from_camera(rule.camera, return_detections=True, return_image=True)
            d: Detection
            for d in all.detections:
                if (d.confidence >= rule.confidence_pct) and re.search(rule.class_regex, d.class_name):
                    LOGGER.debug("Detection triggered")
                    response["triggered"] = True
                    response["image"] = viam_to_pil_image(all.image)
                    response["label"] = d.class_name
        case "classification":
            classifier = _get_vision_service(rule.classifier, resources)
            all = await classifier.capture_all_from_camera(rule.camera, return_classifications=True, return_image=True)
            c: Classification
            for c in all.classifications:
                if (c.confidence >= rule.confidence_pct) and re.search(rule.class_regex, c.class_name):
                    LOGGER.debug("Classification triggered")
                    response["triggered"] = True
                    response["image"] = viam_to_pil_image(all.image)
                    response["label"] = c.class_name
        case "tracker":
            tracker = _get_vision_service(rule.tracker, resources)
            all = await tracker.capture_all_from_camera(rule.camera, return_classifications=False, return_detections=True, return_image=True)
            approved = []
            # we need to get approved list to see if there
            # are detections of any unknown people without known people
            known = await tracker.do_command({"list": True})
            for d in all.detections:
                authorized = False
                for k in known["list"]:
                    if (k["label"] == d.class_name) and (k["authorized"] == True):
                        authorized = True
                approved.append(authorized)
                if not authorized:
                    im = viam_to_pil_image(all.image)
                    response["image"] = im.crop((d.x_min, d.y_min, d.x_max, d.y_max))
                    response["label"] = d.class_name
            LOGGER.debug(approved)
            if len(approved) > 0 and logic.NOR(approved):
                LOGGER.info("Tracker triggered")
                response["triggered"] = True
        case "call":
            try:
                call_res = await call_method(resources, rule.resource, rule.method, rule.payload, None)
                if rule.result_path:
                    call_res = get_value_by_dot_notation(call_res, rule.result_path)
                    if call_res == None:
                        LOGGER.error(f"data not found in path {rule.result_path}")
                        return response

                if rule.result_function:
                    match rule.result_function:
                        case "len":
                            call_res = len(call_res)
                        case "any":
                            call_res = any(call_res)          

                triggered = False
                match rule.result_operator:
                    case "eq":
                        triggered = call_res == rule.result_value
                    case "ne":
                        triggered = call_res != rule.result_value
                    case "lt":
                        triggered = call_res < rule.result_value
                    case "lte":
                        triggered = call_res <= rule.result_value 
                    case "gt":
                        triggered = call_res > rule.result_value
                    case "gte":
                        triggered = call_res >= rule.result_value
                    case "regex":
                        triggered = re.match(rule.result_value, call_res)
                    case "in":
                        triggered = rule.result_value in call_res
                    case "hasattr":
                        triggered = hasattr(call_res, rule.result_value)

                response["triggered"] = triggered
                LOGGER.error(f"call rule eval to {triggered}")
            except Exception as e:
                LOGGER.error(f"Error in 'call' type rule, rule not properly evaluated: {e}")
    return response

def logical_trigger(logic_type, list):
    logic_function = getattr(logic, logic_type)
    return logic_function(list)

def _get_vision_service(name, resources) -> Vision:
    actual = resources['_deps'][VisionClient.get_resource_name(name)]
    if resources.get(actual) == None:
        # initialize if it is not already
        resources[actual] = cast(VisionClient, actual)
    return resources[actual]

def get_value_by_dot_notation(data, path):
    """Access a nested dictionary value using dot notation."""

    keys = path.split('.')
    value = data

    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return None  # Key not found

    return value