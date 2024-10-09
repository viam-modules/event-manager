"""
This file registers the model with the Python SDK.
"""

from viam.services.generic import Generic
from viam.components.sensor import Sensor

from viam.resource.registry import Registry, ResourceCreatorRegistration

from .eventManager import eventManager, eventStatus

Registry.register_resource_creator(Generic.SUBTYPE, eventManager.MODEL, ResourceCreatorRegistration(eventManager.new, eventManager.validate))
Registry.register_resource_creator(Sensor.SUBTYPE, eventStatus.MODEL, ResourceCreatorRegistration(eventStatus.new, eventStatus.validate))
