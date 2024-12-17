import json
from typing import cast
import bson

from viam.components.generic import Generic as GenericComponent
from viam.services.generic import Generic as GenericService
from viam.services.vision import VisionClient
from viam.components.sensor import Sensor

from viam.logging import getLogger

LOGGER = getLogger(__name__)

async def call_method(resources, name, method, payload, event):
    # certainly this could be improved
    if (resources["resources"][name]["type"] == "component") and (resources["resources"][name]["subtype"] == "generic"):
        resource_dep = resources['_deps'][GenericComponent.get_resource_name(name)]
        resource = cast(GenericComponent, resource_dep)
    if (resources["resources"][name]["type"] == "component") and (resources["resources"][name]["subtype"] == "sensor"):
        resource_dep = resources['_deps'][Sensor.get_resource_name(name)]
        resource = cast(Sensor, resource_dep)
    if (resources["resources"][name]["type"] == "service") and (resources["resources"][name]["subtype"] == "generic"):
        resource_dep = resources['_deps'][GenericService.get_resource_name(name)]
        resource = cast(GenericService, resource_dep)
    if (resources["resources"][name]["type"] == "service") and (resources["resources"][name]["subtype"] == "vision"):
        resource_dep = resources['_deps'][VisionClient.get_resource_name(name)]
        resource = cast(VisionClient, resource_dep)

    method = getattr(resource, method)

    if payload:
        if (event):        
            return await method(update_and_return_json_payload(payload, event))
    else:
        return await method()
    
async def query_data(app_client, action_data_management_response, event, notification):
    query = []
    json_query = update_and_return_json_payload(json.dumps(action_data_management_response["query"]), event, notification)
    LOGGER.debug(json_query)
    for obj in json_query:
        query.append(bson.encode(obj))
    query.append(bson.encode({ "$limit": 1 }))

    tabular_data = await app_client.data_client.tabular_data_by_mql(organization_id=action_data_management_response["organization_id"], mql_binary=query)
    
    LOGGER.debug(tabular_data)
    if len(tabular_data) == 1:
        LOGGER.debug(tabular_data[0])
        return get_value_by_dot_notation(tabular_data[0], action_data_management_response["result_path"])
    else:
        return None
    
def update_and_return_json_payload(payload, event, notification):
    payload_copy = payload

    if (event):
    # At some point we might want other things to be template variables, for now just label and event name
        payload_copy = payload_copy.replace('<<triggered_label>>', event.triggered_label)
        payload_copy = payload_copy.replace('<<event_name>>', event.name)
    
    if (notification):
        to = notification.to
        if not to.startswith("+"):
            to = "+1" + to
        payload_copy = payload_copy.replace('<<notification_to>>', to)

    return json.loads(payload_copy.replace("'", "\""))

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