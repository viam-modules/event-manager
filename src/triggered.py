import os
import shutil
import re
import asyncio
from PIL import Image
from viam.proto.app.data import Filter
from viam.components.camera import CameraClient, Camera
from typing import cast
from datetime import datetime, timedelta

import io

from viam.logging import getLogger

LOGGER = getLogger(__name__)

async def request_capture(camera:str, event_video_capture_padding_secs:int, resources:dict):
    vs = _get_video_store(camera, resources)

    current_time = datetime.now()

    # Format the current time
    formatted_time_current = current_time.strftime('%Y-%m-%d_%H-%M-%S')

    # we want X seconds before and after, so subtract X*2 from current time
    time_minus = current_time - timedelta(seconds=(event_video_capture_padding_secs*2))

    # Format the time minus X*2
    formatted_time_minus = time_minus.strftime('%Y-%m-%d_%H-%M-%S')

    store_args = { "command": "save",
        "from": formatted_time_minus,
        "to": formatted_time_current,
        "metadata": camera
    }

    LOGGER.error(store_args)
    
    store_result = await vs.do_command( store_args )

    return store_result.filename

async def get_triggered_cloud(camera:str=None, event:str=None, num:int=5, app_client:str=None):
    pattern = _create_match_pattern(camera, event, None, False)
    filter_args = {}
    if camera:
        filter_args['component_name'] = camera
    tags = await app_client.data_client.tags_by_filter(Filter(**filter_args))
    matched = []
    for tag in tags:
        if re.match(pattern, tag):
            spl = tag.split('--')
            matched.insert(0, {"event": spl[1].replace('_', ' '), "camera": spl[2], "time": spl[3], "id": tag })
    return matched

# deletes tags from the cloud, not the actual images
async def delete_from_cloud(camera:str=None, event:str=None, id:str=None, app_client:str=None):
    pattern = _create_match_pattern(camera, event, id, False)
    filter_args = {}
    if camera:
        filter_args['component_name'] = camera
    tags = await app_client.data_client.tags_by_filter(Filter(**filter_args))
    matched = []
    for tag in tags:
        if re.match(pattern, tag):
            spl = tag.split('--')
            matched.append(tag)
    
    resp = await app_client.data_client.remove_tags_from_binary_data_by_filter(tags=matched, filter=Filter(**filter_args))
    return

def _name_clean(cam_name):
    return cam_name.replace(' ','_')

def _create_match_pattern(camera:str=None, event:str=None, id:str=None, use_filesystem:bool=False):
    prefix = ''
    pattern = prefix + 'SAVCAM--'
    if event != None:
        pattern = pattern + event + "--"
    else:
        pattern = pattern + ".*--"
    if camera != None:
        pattern = pattern + camera + "--.*"
    else:
        pattern = pattern + ".*--.*"
    if id != None:
        pattern = prefix + id
    return pattern

def _label(event_name, cam_name, event_id, use_filesystem):
    prefix = ''
    return _name_clean(f"{prefix}SAVCAM--{event_name}--{cam_name}--{event_id}")

def _get_video_store(name, resources) -> Camera:
    actual = resources['_deps'][CameraClient.get_resource_name(resources["camera_config"][name]["video_capture_camera"])]
    if resources.get(actual) == None:
        # initialize if it is not already
        resources[actual] = cast(CameraClient, actual)
    return resources[actual]