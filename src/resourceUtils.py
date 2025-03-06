import json
from typing import cast

from viam.components.generic import Generic as GenericComponent
from viam.services.generic import Generic as GenericService
from viam.services.vision import VisionClient
from viam.components.sensor import Sensor


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
        # we don't want to alter action.payload directly as it will be used as a template repeatedly
        payload_copy = payload

        if (event):
        # At some point we might want other things to be template variables, for now just label and event name
            payload_copy = payload_copy.replace('<<triggered_label>>', event.triggered_label)
            payload_copy = payload_copy.replace('<<triggered_camera>>', event.triggered_camera)
            payload_copy = payload_copy.replace('<<event_name>>', event.name)
        
            return await method(json.loads(payload_copy.replace("'", "\"")))
    else:
        return await method()