import os
import shutil
import re
import asyncio
from PIL import Image
from viam.proto.app.data import Filter
from viam.components.camera import CameraClient, Camera
from viam.app.viam_client import ViamClient
from viam.gen.app.data.v1.data_pb2 import ORDER_DESCENDING
from viam.proto.app.data import BinaryID

from typing import cast
from datetime import datetime, timedelta

import io

from viam.logging import getLogger

LOGGER = getLogger(__name__)

async def request_capture(camera:str, event_name:str, event_video_capture_padding_secs:int, resources:dict):
    vs = _get_video_store(camera, resources)

    # sleep for additional seconds in order to capture more video
    await asyncio.sleep(event_video_capture_padding_secs)

    current_time = datetime.now()
    # go back a second to ensure its not the current second
    current_time = current_time - timedelta(seconds=1)

    # Format the current time
    formatted_time_current = current_time.strftime('%Y-%m-%d_%H-%M-%S')

    # we want X seconds before and after, so subtract X*2 from current time
    time_minus = current_time - timedelta(seconds=(event_video_capture_padding_secs*2))

    # Format the time minus X*2
    formatted_time_minus = time_minus.strftime('%Y-%m-%d_%H-%M-%S')

    store_args = { "command": "save",
        "from": formatted_time_minus,
        "to": formatted_time_current,
        "metadata": _label(event_name, camera)
    }
    
    store_result = await vs.do_command( store_args )
    return store_result

async def get_triggered_cloud(camera:str=None, event:str=None, num:int=5, app_client:ViamClient=None):
    filter_args = {}
    videos = await app_client.data_client.binary_data_by_filter(filter=Filter(**filter_args), include_binary_data=False, limit=100, sort_order=ORDER_DESCENDING)
    pattern = _create_match_pattern(camera, event, None)
    matched = []
    for video in videos[0]:
        LOGGER.debug(video.metadata)
        LOGGER.debug(pattern)
        if re.match(pattern, video.metadata.file_name):
            spl = video.metadata.file_name.split('--')
            matched.append({"event": spl[1].replace('_', ' '), "camera": spl[2].replace('.mp4',''), 
                            "time": video.metadata.time_requested.seconds, "id": video.metadata.id, 
                            "organization_id": video.metadata.capture_metadata.organization_id, "location_id":  video.metadata.capture_metadata.location_id})
            if len(matched) == num:
                break
    return matched

# deletes video from the cloud
async def delete_from_cloud(id:str=None, organization_id:str=None, location_id:str=None, app_client:ViamClient=None):    
    resp = await app_client.data_client.delete_binary_data_by_ids(binary_ids=[BinaryID(file_id=id, organization_id=organization_id, location_id=location_id)])
    return resp

def _name_clean(string):
    return string.replace(' ','_')

def _create_match_pattern(camera:str=None, event:str=None, id:str=None):
    pattern = '.*_SAVCAM--'
    if event != None:
        pattern = pattern + _name_clean(event) + "--"
    else:
        pattern = pattern + ".*--"
    if camera != None:
        pattern = pattern + camera + ".mp4"
    else:
        pattern = pattern + ".*\\.mp4"
    if id != None:
        pattern = id
    return pattern

def _label(event_name, cam_name):
    return _name_clean(f"SAVCAM--{event_name}--{cam_name}")

def _get_video_store(name, resources) -> Camera:
    actual = resources['_deps'][CameraClient.get_resource_name(resources["camera_config"][name]["video_capture_camera"])]
    if resources.get(actual) == None:
        # initialize if it is not already
        resources[actual] = cast(CameraClient, actual)
    return resources[actual]