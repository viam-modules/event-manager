import re
import asyncio

from datetime import datetime
from typing import cast
from PIL import Image
from . import logic
from . import triggered

from viam.components.camera import Camera
from viam.media.video import ViamImage
from viam.services.vision import VisionClient, Detection, Classification
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
    detector: str
    cameras: list[str]
    class_regex: str
    confidence_pct: float
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            self.__dict__[key] = value
class RuleClassifier():
    type: str="classification"
    classifier: str
    cameras: list[str]
    class_regex: str
    confidence_pct: float
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

async def eval_rule(rule:RuleTime|RuleDetector|RuleClassifier, event_name, resources):
    triggered = False

    match rule.type:
        case "time":
            curr_time = datetime.now()
            for r in rule.ranges:
                if (curr_time.hour >= r.start_hour) and (curr_time.hour < r.end_hour):
                    LOGGER.debug("Time triggered")
                    triggered = True   
        case "detection":
            detector = _get_vision_service(rule.detector, resources)
            for camera_name in rule.cameras:
                cam = await _get_camera(camera_name, resources)
                img = cam.last_image

                detections = await detector.get_detections(img)
                d: Detection
                for d in detections:
                    if (d.confidence >= rule.confidence_pct) and re.search(rule.class_regex, d.class_name):
                        LOGGER.debug("Detection triggered")
                        triggered = True
        case "classification":
            classifier = _get_vision_service(rule.classifier, resources)
            for camera_name in rule.cameras:
                cam = await _get_camera(camera_name, resources)
                img = cam.last_image

                classifications = await classifier.get_classifications(img, 3)
                c: Classification
                for c in classifications:
                    if (c.confidence >= rule.confidence_pct) and re.search(rule.class_regex, c.class_name):
                        LOGGER.debug("Classification triggered")
                        triggered = True

    return triggered

def logical_trigger(logic_type, list):
    logic_function = getattr(logic, logic_type)
    return logic_function(list)

async def _get_camera(camera_name, resources) -> CameraCache:
    if resources.get(camera_name) == None:
        # initialize camera if it is not already
        actual_camera = resources['_deps'][Camera.get_resource_name(camera_name)]
        resources[camera_name] = CameraCache
        resources[camera_name].camera = cast(Camera, actual_camera)
        resources[camera_name].last_image = await resources[camera_name].camera.get_image()
        asyncio.ensure_future(_cam_image_loop(resources, camera_name))
    return resources[camera_name]

def _get_vision_service(name, resources):
    actual = resources['_deps'][VisionClient.get_resource_name(name)]
    if resources.get(actual) == None:
        # initialize if it is not already
        resources[actual] = cast(VisionClient, actual)
    return resources[actual]

async def _cam_image_loop(resources, cam_name):
    LOGGER.info("START CAM LOOP")
    while True:
        resources[cam_name].last_image = await resources[cam_name].camera.get_image()
        triggered.push_buffer(resources, cam_name, viam_to_pil_image(resources[cam_name].last_image))
        await asyncio.sleep(.005)