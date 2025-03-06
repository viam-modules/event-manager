import bson
import asyncio

from PIL import Image
from viam.proto.app.data import Filter
from viam.components.camera import CameraClient, Camera
from viam.app.viam_client import ViamClient
from viam.gen.app.data.v1.data_pb2 import ORDER_DESCENDING
from viam.proto.app.data import BinaryID, Order
from .globals import shared_state
from typing import cast
from datetime import datetime, timedelta, timezone

import io

LOGGER = shared_state['logger']

async def request_capture(event, resources:dict):
    vs = _get_video_store(event.video_capture_resource, resources)

    await asyncio.sleep(event.event_video_capture_padding_secs)
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
    
    try:
        store_result = await vs.do_command( store_args )
        return store_result
    except Exception as e:
        LOGGER.error(e)

async def get_triggered_cloud(event_manager_name:str=None,organization_id:str=None, event_name:str=None, num:int=5, app_client:ViamClient=None):
    if (app_client): 
        filter_args = {}
        matched = []
        matched_index_by_dt = {}

        # first get recent tabular data, as this is the "data of record"
        # Note: the assumption is made that no other tabular data is being stored for this component
        query = []
        match = {"component_name": event_manager_name}
        if event_name != None:
            match[f"data.readings.state.{event_name}" ] = { "$exists": True }
            query.append(bson.encode({ "$match": { f"data.readings.state.{event_name}" : { "$exists": True }}}))
        query.append(bson.encode({ "$match": match }))
        query.append(bson.encode({ "$sort": { "time_received": -1 } }))
        query.append(bson.encode({ "$limit": num }))
    
        tabular_data = await app_client.data_client.tabular_data_by_mql(organization_id=organization_id, mql_binary=query)
        for tabular in tabular_data:
            state = tabular["data"]["readings"]["state"]
            for reading in state:
                if event_name == None or event_name == reading:
                    matched_index_by_dt[state[reading]["last_triggered"]] = len(matched)
                    triggered_camera = ""
                    if "triggered_camera" in state[reading]:
                        triggered_camera = state[reading]["triggered_camera"]
                    matched.append({"event": reading, "time": state[reading]["last_triggered"],
                                    "location_id": tabular["location_id"], "organization_id": tabular["organization_id"], "triggered_camera": triggered_camera })
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
                    LOGGER.debug(video)
                    matched[matched_index_by_dt[vtime]]["video_id"] = video.metadata.id
        return matched
    else:
        return { "error": "app_api_key and app_api_key_id as well as data capture on GetReadings() for this module must be configured" }

# deletes video from the cloud
async def delete_from_cloud(id:str=None, organization_id:str=None, location_id:str=None, app_client:ViamClient=None):
    if (app_client): 
        resp = await app_client.data_client.delete_binary_data_by_ids(binary_ids=[BinaryID(file_id=id, organization_id=organization_id, location_id=location_id)])
        return resp
    else:
        return { "error": "app_api_key and app_api_key_id as well as data capture on GetReadings() for this module must be configured" }
def _name_clean(string):
    return string.replace(' ','_')

def _label(event_name, cam_name, last_triggered):
    return _name_clean(f"SAVCAM--{event_name}--{cam_name}--{str(last_triggered)}")

def _get_video_store(name, resources) -> Camera:
    actual = resources['_deps'][CameraClient.get_resource_name(name)]
    if resources.get(actual) == None:
        # initialize if it is not already
        resources[actual] = cast(CameraClient, actual)
    return resources[actual]