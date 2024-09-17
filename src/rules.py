import re
import asyncio

from datetime import datetime
from typing import cast
from PIL import Image
from . import logic
from . import triggered

from viam.components.camera import Camera
from viam.media.video import ViamImage
from viam.services.vision import VisionClient, Detection, Classification, Vision
from viam.logging import getLogger
from viam.media.utils.pil import viam_to_pil_image

LOGGER = getLogger(__name__)
CAM_BUFFER_SIZE = 75

class TimeRange():
    start_hour: int
    end_hour: int
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            self.__dict__[key] = value

class RuleDetector():
    type: str="detection"
    cameras: list[str]
    class_regex: str
    confidence_pct: float
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            self.__dict__[key] = value
class RuleClassifier():
    type: str="classification"
    cameras: list[str]
    class_regex: str
    confidence_pct: float
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            self.__dict__[key] = value

class RuleTracker():
    type: str="tracker"
    cameras: list[str]
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

class CameraCache():
    camera: Camera
    last_image: ViamImage

async def eval_rule(rule:RuleTime|RuleDetector|RuleClassifier|RuleTracker, resources):
    triggered = False
    image = None
    match rule.type:
        case "time":
            curr_time = datetime.now()
            for r in rule.ranges:
                if (curr_time.hour >= r.start_hour) and (curr_time.hour < r.end_hour):
                    LOGGER.debug("Time triggered")
                    triggered = True   
        case "detection":
            for camera_name in rule.cameras:
                detector = _get_vision_service(camera_name, resources)
                all = await detector.capture_all_from_camera(camera_name, return_detections=True, return_image=True)
                d: Detection
                for d in all.detections:
                    if (d.confidence >= rule.confidence_pct) and re.search(rule.class_regex, d.class_name):
                        LOGGER.debug("Detection triggered")
                        triggered = True
                        image = viam_to_pil_image(all.image)
                        image.save("/Users/mcvella/git/security-event-manager/test.jpg")
        case "classification":
            for camera_name in rule.cameras:
                classifier = _get_vision_service(camera_name, resources)
                all = await classifier.capture_all_from_camera(camera_name, return_classifications=True, return_image=True)
                c: Classification
                for c in all.classifications:
                    if (c.confidence >= rule.confidence_pct) and re.search(rule.class_regex, c.class_name):
                        LOGGER.debug("Classification triggered")
                        triggered = True
                        image = viam_to_pil_image(all.image)
        case "tracker":
            for camera_name in rule.cameras:
                tracker = _get_vision_service(camera_name, resources)
                LOGGER.error("checking")
                all = await tracker.capture_all_from_camera(camera_name, return_classifications=True, return_detections=True, return_image=True)
                c: Classification
                for c in all.classifications:
                    LOGGER.error(c)
                    not_approved = False
                    for d in all.detections:
                        # TODO - add logic here to compare to approved list
                        not_approved = True
                        im = viam_to_pil_image(all.image)
                        image = im.crop((d.x_min, d.y_min, d.x_max, d.y_max))
                        break
                    if not_approved == True:
                        LOGGER.debug("Tracker triggered")
                        triggered = True
    return { "triggered" : triggered, "image": image }

def logical_trigger(logic_type, list):
    logic_function = getattr(logic, logic_type)
    return logic_function(list)

def _get_vision_service(name, resources) -> Vision:
    actual = resources['_deps'][VisionClient.get_resource_name(resources["camera_config"][name]["vision_service"])]
    if resources.get(actual) == None:
        # initialize if it is not already
        resources[actual] = cast(VisionClient, actual)
    return resources[actual]