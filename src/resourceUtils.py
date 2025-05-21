import json
from typing import cast, Dict, Any, Optional, Protocol, runtime_checkable, Union

from viam.components.generic import Generic as GenericComponent
from viam.services.generic import Generic as GenericService
from viam.services.vision import VisionClient
from viam.components.sensor import Sensor
from viam.components.motor import Motor
from viam.resource.base import ResourceBase

@runtime_checkable
class EventLike(Protocol):
    """Protocol for objects that have event-like properties."""
    name: str
    triggered_label: str
    triggered_camera: str


async def call_method(
    resources: Dict[str, Any], 
    name: str, 
    method: str, 
    payload: Optional[str], 
    event: Optional[Any]  # Keep Any to ensure backward compatibility
) -> Any:
    """Call a method on a resource with optional payload.
    
    Args:
        resources: Dictionary of resources
        name: Name of the resource
        method: Method name to call on the resource
        payload: Optional JSON payload as string
        event: Optional Event object (must have name, triggered_label and triggered_camera attributes)
        
    Returns:
        Result of the method call
    """
    # certainly this could be improved
    resource: ResourceBase
    
    if (resources["resources"][name]["type"] == "component") and (resources["resources"][name]["subtype"] == "generic"):
        resource_dep = resources['_deps'][GenericComponent.get_resource_name(name)]
        resource = cast(GenericComponent, resource_dep)
    if (resources["resources"][name]["type"] == "component") and (resources["resources"][name]["subtype"] == "sensor"):
        resource_dep = resources['_deps'][Sensor.get_resource_name(name)]
        resource = cast(Sensor, resource_dep)
    if (resources["resources"][name]["type"] == "component") and (resources["resources"][name]["subtype"] == "motor"):
        resource_dep = resources['_deps'][Motor.get_resource_name(name)]
        resource = cast(Motor, resource_dep)
    if (resources["resources"][name]["type"] == "service") and (resources["resources"][name]["subtype"] == "generic"):
        resource_dep = resources['_deps'][GenericService.get_resource_name(name)]
        resource = cast(GenericService, resource_dep)
    if (resources["resources"][name]["type"] == "service") and (resources["resources"][name]["subtype"] == "vision"):
        resource_dep = resources['_deps'][VisionClient.get_resource_name(name)]
        resource = cast(VisionClient, resource_dep)

    method_fn = getattr(resource, method)

    if payload:
        # we don't want to alter action.payload directly as it will be used as a template repeatedly
        payload_copy = payload

        if event:
            # At some point we might want other things to be template variables, for now just label and event name
            payload_copy = payload_copy.replace('<<triggered_label>>', event.triggered_label)
            payload_copy = payload_copy.replace('<<triggered_camera>>', event.triggered_camera)
            payload_copy = payload_copy.replace('<<event_name>>', event.name)
        
        return await method_fn(json.loads(payload_copy.replace("'", "\"")))
    else:
        return await method_fn()