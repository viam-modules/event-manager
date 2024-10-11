import os
import shutil
import re
import asyncio
from PIL import Image
from viam.proto.app.data import Filter
from viam.components.camera import CameraClient, Camera
from viam.app.viam_client import ViamClient
from viam.gen.app.data.v1.data_pb2 import ORDER_DESCENDING
from viam.proto.app.data import BinaryID, Order
from typing import cast
from datetime import datetime, timedelta, timezone

import io

from viam.logging import getLogger

LOGGER = getLogger(__name__)

async def request_capture(event, resources:dict):
    vs = _get_video_store(event.video_capture_resource, resources)

    current_time = datetime.now()
    # go back a second to ensure its not the current second
    current_time = current_time - timedelta(seconds=1)

    # Format the current time
    formatted_time_current = current_time.strftime('%Y-%m-%d_%H-%M-%S')

    # we want X seconds before and after, so subtract X*2 from current time
    time_minus = current_time - timedelta(seconds=(event.event_video_capture_padding_secs*2))

    # Format the time minus X*2
    formatted_time_minus = time_minus.strftime('%Y-%m-%d_%H-%M-%S')

    store_args = { "command": "save",
        "from": formatted_time_minus,
        "to": formatted_time_current,
        "metadata": _label(event.name, event.video_capture_resource, event.last_triggered),
        "async": True
    }
    
    store_result = await vs.do_command( store_args )
    return store_result

async def get_triggered_cloud(event_name:str=None, num:int=5, app_client:ViamClient=None):
    filter_args = {}
    matched = []
    matched_index_by_dt = {}

    # first get recent tabular data, as this is the "data of record"
    # TODO: currently there is an assumption that no other tabular data is being stored.  Improve this.
    tabular_data = await app_client.data_client.tabular_data_by_filter(filter=Filter(**filter_args), limit=100, sort_order=Order.ORDER_DESCENDING)
    for tabluar in tabular_data[0]:
        state = tabluar.data["readings"]["state"]
        for reading in state:
            if event_name == None or event_name == reading:
                matched_index_by_dt[state[reading]["last_triggered"]] = len(matched)
                matched.append({"event": reading, "time": state[reading]["last_triggered"],
                                "location_id": tabluar.metadata.location_id, "organization_id": tabluar.metadata.organization_id })
            if len(matched) == num:
                break
        if len(matched) == num:
            break

    # now try to match any videos based on event timestamp
    videos = await app_client.data_client.binary_data_by_filter(filter=Filter(**filter_args), include_binary_data=False, limit=100, sort_order=Order.ORDER_DESCENDING)
    for video in videos[0]:
        LOGGER.debug(video.metadata)
        spl = video.metadata.file_name.split('--')
        if len(spl) > 3:
            vtime = datetime.fromtimestamp( int(float(spl[3].replace('.mp4',''))), timezone.utc).isoformat() + 'Z'
            if vtime in matched_index_by_dt:
                matched[matched_index_by_dt[vtime]]["video_id"] = video.metadata.id
    return matched

# deletes video from the cloud
async def delete_from_cloud(id:str=None, organization_id:str=None, location_id:str=None, app_client:ViamClient=None):    
    resp = await app_client.data_client.delete_binary_data_by_ids(binary_ids=[BinaryID(file_id=id, organization_id=organization_id, location_id=location_id)])
    return resp

def _name_clean(string):
    return string.replace(' ','_')

def _create_match_pattern(camera:str=None, event_name:str=None, id:str=None):
    pattern = '.*_SAVCAM--'
    if event_name != None:
        pattern = pattern + _name_clean(event_name) + "--"
    else:
        pattern = pattern + ".*--"
    if camera != None:
        pattern = pattern + camera + "--.*\\.mp4"
    else:
        pattern = pattern + ".*\\.mp4"
    if id != None:
        pattern = id
    return pattern

def _label(event_name, cam_name, last_triggered):
    return _name_clean(f"SAVCAM--{event_name}--{cam_name}--{str(last_triggered)}")

def _get_video_store(name, resources) -> Camera:
    actual = resources['_deps'][CameraClient.get_resource_name(name)]
    if resources.get(actual) == None:
        # initialize if it is not already
        resources[actual] = cast(CameraClient, actual)
    return resources[actual]