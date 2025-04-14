import re
import asyncio
from datetime import datetime
from typing import cast, Dict, Any, List, Union, Optional, TypeVar, Callable, Tuple, overload
from PIL import Image
from . import logic
from .resourceUtils import call_method
from .globals import getParam
from viam.services.vision import VisionClient, Detection, Classification, Vision
from viam.media.utils.pil import viam_to_pil_image


class TimeRange():
    start_hour: int
    end_hour: int

    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            self.__dict__[key] = value

class RuleDetector():
    type: str="detection"
    camera: str
    detector: str
    class_regex: str
    confidence_pct: float
    inverse_pause_secs: int

    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            self.__dict__[key] = value
class RuleClassifier():
    type: str="classification"
    camera: str
    classifier: str
    class_regex: str
    confidence_pct: float
    inverse_pause_secs: int

    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            self.__dict__[key] = value

class RuleTracker():
    type: str="tracker"
    camera: str
    tracker: str
    inverse_pause_secs: int
    pause_on_known_secs: int

    def __init__(self, **kwargs: Any) -> None:
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
    result_value: Any
    inverse_pause_secs: int

    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            self.__dict__[key] = value
class RuleTime():
    type: str="time"
    ranges: list[TimeRange]
    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            if isinstance(value, list):
                self.__dict__[key] = []
                for item in value:
                     self.__dict__[key].append(TimeRange(**item))
            else:
                self.__dict__[key] = value

RuleType = Union[RuleTime, RuleDetector, RuleClassifier, RuleTracker, RuleCall]

async def eval_rule(rule: RuleType, resources: Dict[str, Any]) -> Dict[str, Any]:
    response: Dict[str, Any] = { "triggered" : False }
    match rule.type:
        case "time":
            curr_time = datetime.now()
            if isinstance(rule, RuleTime):  # Type narrowing
                for r in rule.ranges:
                    if (curr_time.hour >= r.start_hour) and (curr_time.hour < r.end_hour):
                        getParam('logger').debug("Time triggered")
                        response["triggered"] = True   
        case "detection":
            if isinstance(rule, RuleDetector):  # Type narrowing
                detector = _get_vision_service(rule.detector, resources)
                all = await detector.capture_all_from_camera(rule.camera, return_detections=True, return_image=True)
                d: Detection
                if all.detections is not None:
                    for d in all.detections:
                        if (d.confidence >= rule.confidence_pct) and re.search(rule.class_regex, d.class_name):
                            getParam('logger').debug("Detection triggered")
                            response["triggered"] = True
                            if all.image is not None:
                                response["image"] = viam_to_pil_image(all.image)
                            response["value"] = d.class_name
                            response["resource"] = rule.camera
        case "classification":
            if isinstance(rule, RuleClassifier):  # Type narrowing
                classifier = _get_vision_service(rule.classifier, resources)
                all = await classifier.capture_all_from_camera(rule.camera, return_classifications=True, return_image=True)
                c: Classification
                if all.classifications is not None:
                    for c in all.classifications:
                        if (c.confidence >= rule.confidence_pct) and re.search(rule.class_regex, c.class_name):
                            getParam('logger').debug("Classification triggered")
                            response["triggered"] = True
                            if all.image is not None:
                                response["image"] = viam_to_pil_image(all.image)
                            response["value"] = c.class_name
                            response["resource"] = rule.camera
        case "tracker":
            if isinstance(rule, RuleTracker):  # Type narrowing
                tracker = _get_vision_service(rule.tracker, resources)
                # NOTE: we call capture_all_from_camera() in order to get an image and coordinates in case there is an actionable detection
                all = await tracker.capture_all_from_camera(rule.camera, return_classifications=False, return_detections=True, return_image=True)
                approved_status: List[bool] = []

                current = await tracker.do_command({"list_current": True})
                
                if all.detections is not None:
                    for d in all.detections:
                        authorized = False

                        # NOTE: the class name of a tracker detection that has been labeled will have a label appended to it,
                        #  so we strip this label to match against the keys in current["list_current"]
                        class_without_label = re.sub(r'\s+\(label:\s.*', '', d.class_name)
                        list_current = current.get("list_current", {})
                        getParam('logger').debug(class_without_label + "-" + str(list_current))

                        if isinstance(list_current, dict) and class_without_label in list_current:
                            k = list_current[class_without_label]
                            if isinstance(k, dict) and (k.get("face_id_label") or k.get("manual_label") or k.get("re_id_label")):
                                authorized = True
                                response["known_person_seen"] = True
                            approved_status.append(authorized)
                            if not authorized and all.image is not None:
                                response["image"] = viam_to_pil_image(all.image).crop((d.x_min, d.y_min, d.x_max, d.y_max))
                                response["value"] = class_without_label
                                response["resource"] = rule.camera
                getParam('logger').debug(approved_status)
                if len(approved_status) > 0 and logic.NOR(approved_status):
                    getParam('logger').info("Tracker triggered")
                    getParam('logger').info(response)

                    response["triggered"] = True
        case "call":
            try:
                if isinstance(rule, RuleCall):  # Type narrowing
                    call_res = await call_method(resources, rule.resource, rule.method, rule.payload, None)
                    if rule.result_path:
                        call_res = get_value_by_dot_notation(call_res, rule.result_path)
                        if call_res == None:
                            getParam('logger').error(f"data not found in path {rule.result_path}")
                            return response

                    getParam('logger').debug(call_res)
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
                            triggered = re.match(rule.result_value, call_res) is not None
                        case "in":
                            triggered = rule.result_value in call_res
                        case "hasattr":
                            triggered = hasattr(call_res, rule.result_value)

                    response["triggered"] = triggered
                    response["value"] = call_res
                    response["resource"] = rule.resource
                    getParam('logger').debug(f"call rule eval to {triggered} call_res {call_res} result_val {rule.result_value}")
            except Exception as e:
                getParam('logger').error(f"Error in 'call' type rule, rule not properly evaluated: {e}")
    return response

def logical_trigger(logic_type: str, list: List[bool]) -> bool:
    logic_function = getattr(logic, logic_type)
    return logic_function(list)

def _get_vision_service(name: str, resources: Dict[str, Any]) -> Vision:
    actual = resources['_deps'][VisionClient.get_resource_name(name)]
    if resources.get(actual) == None:
        # initialize if it is not already
        resources[actual] = cast(VisionClient, actual)
    return resources[actual]

def get_value_by_dot_notation(data: Any, path: str) -> Optional[Any]:
    """Access a nested dictionary value using dot notation."""

    keys = path.split('.')
    value = data

    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return None  # Key not found

    return value