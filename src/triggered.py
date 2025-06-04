import bson
import asyncio
from typing import Dict, Any, List, Optional, Union, TypeVar, Tuple, cast

from PIL import Image
from viam.proto.app.data import Filter
from viam.components.camera import CameraClient, Camera
from viam.components.generic import GenericClient, Generic
from viam.app.viam_client import ViamClient
from viam.gen.app.data.v1.data_pb2 import ORDER_DESCENDING
from viam.proto.app.data import BinaryID, Order
from .globals import getParam
from . import events
from datetime import datetime, timedelta, timezone

import io

async def request_capture(event: events.Event, resources: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Request video capture for an event
    
    Args:
        event: The event that triggered capture
        resources: Dictionary of available resources
        
    Returns:
        Result of the capture command or None if there was an error
    """
    vs = _get_video_store(event.video_capture_resource, resources)
    
    # Calculate capture window based on event trigger time and padding
    from_time = datetime.fromtimestamp(event.last_triggered - event.event_video_capture_padding_secs, timezone.utc)
    to_time = datetime.fromtimestamp(event.last_triggered + event.event_video_capture_padding_secs, timezone.utc)
    
    # Calculate how long we need to sleep to reach to_time + 1 second
    current_time = datetime.now(timezone.utc)
    target_time = to_time + timedelta(seconds=1)
    if current_time < target_time:
        sleep_seconds = (target_time - current_time).total_seconds()
        await asyncio.sleep(sleep_seconds)

    # Format the times
    formatted_time_from = from_time.strftime('%Y-%m-%d_%H-%M-%S')
    formatted_time_to = to_time.strftime('%Y-%m-%d_%H-%M-%S')

    store_args: Dict[str, Any] = { 
        "command": "save",
        "from": formatted_time_from,
        "to": formatted_time_to,
        "metadata": _label(event.name, event.video_capture_resource, event.last_triggered),
        "async": True
    }
    
    try:
        store_result = await vs.do_command(store_args)
        return cast(Dict[str, Any], store_result)
    except Exception as e:
        getParam('logger').error(f"Error requesting video capture for event {event.name}: {str(e)}")
        return None

async def get_triggered_cloud(
    event_manager_name: Optional[str]=None, 
    organization_id: Optional[str]=None, 
    event_name: Optional[str]=None, 
    num: int=5, 
    app_client: Optional[ViamClient]=None
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
    """Get triggered events from the cloud
    
    Args:
        event_manager_name: Name of the event manager
        organization_id: ID of the organization
        event_name: Optional name of a specific event to filter by
        num: Maximum number of events to retrieve
        app_client: Viam client for cloud access
        
    Returns:
        List of triggered events or error dictionary
    """
    if (app_client): 
        filter_args: Dict[str, Any] = {}
        matched: List[Dict[str, Any]] = []
        matched_index_by_dt: Dict[str, int] = {}

        # first get recent tabular data, as this is the "data of record"
        # Note: the assumption is made that no other tabular data is being stored for this component
        query: List[bytes] = []
        match: Dict[str, Any] = {"component_name": event_manager_name}
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
                    matched.append({
                        "event": reading, 
                        "time": state[reading]["last_triggered"],
                        "location_id": tabular["location_id"], 
                        "organization_id": tabular["organization_id"], 
                        "triggered_camera": triggered_camera 
                    })
                if len(matched) == num:
                    break
            if len(matched) == num:
                break

        # now try to match any videos based on event timestamp
        videos = await app_client.data_client.binary_data_by_filter(
            filter=Filter(**filter_args), 
            include_binary_data=False, 
            limit=100, 
            sort_order=Order.ORDER_DESCENDING
        )
        for video in videos[0]:
            getParam('logger').debug(video.metadata)
            spl = video.metadata.file_name.split('--')
            if len(spl) > 3:
                vtime = datetime.fromtimestamp(int(float(spl[3].replace('.mp4',''))), timezone.utc).isoformat() + 'Z'
                if vtime in matched_index_by_dt:
                    getParam('logger').debug(video)
                    matched[matched_index_by_dt[vtime]]["video_id"] = video.metadata.id
        return matched
    else:
        return { "error": "app_api_key and app_api_key_id as well as data capture on GetReadings() for this module must be configured" }

async def delete_from_cloud(
    id: Optional[str]=None, 
    organization_id: Optional[str]=None, 
    location_id: Optional[str]=None, 
    app_client: Optional[ViamClient]=None
) -> Dict[str, Any]:
    """Delete a video from the cloud
    
    Args:
        id: ID of the video to delete
        organization_id: ID of the organization
        location_id: ID of the location
        app_client: Viam client for cloud access
        
    Returns:
        Response from delete operation or error dictionary
    """
    if app_client and id and organization_id and location_id:
        resp = await app_client.data_client.delete_binary_data_by_ids(
            binary_ids=[BinaryID(file_id=id, organization_id=organization_id, location_id=location_id)]
        )
        return cast(Dict[str, Any], resp)
    else:
        return { "error": "app_api_key and app_api_key_id as well as data capture on GetReadings() for this module must be configured" }

def _name_clean(string: str) -> str:
    """Clean a string by replacing spaces with underscores
    
    Args:
        string: String to clean
        
    Returns:
        Cleaned string
    """
    return string.replace(' ','_')

def _label(event_name: str, cam_name: str, last_triggered: float) -> str:
    """Create a label for a video capture
    
    Args:
        event_name: Name of the event
        cam_name: Name of the camera
        last_triggered: Timestamp when the event was triggered
        
    Returns:
        Formatted label string
    """
    return _name_clean(f"SAVCAM--{event_name}--{cam_name}--{str(last_triggered)}")

def _get_video_store(name: str, resources: Dict[str, Any]) -> Generic:
    """Get the video store resource
    
    Args:
        name: Name of the video store
        resources: Dictionary of available resources
        
    Returns:
        Video store resource
    """
    # newer versions of video-store resource are Generic, older are Camera
    is_generic = True
    resource_name = GenericClient.get_resource_name(name)
    if resource_name not in resources['_deps']:
        resource_name = CameraClient.get_resource_name(name)
        is_generic = False
    actual = resources['_deps'][resource_name]
    if resources.get(actual) == None:
        # initialize if it is not already
        if is_generic:
            resources[actual] = cast(GenericClient, actual)
        else:
            resources[actual] = cast(CameraClient, actual)
    return resources[actual]
