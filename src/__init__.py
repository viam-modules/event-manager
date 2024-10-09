"""
This file registers the model with the Python SDK.
"""

from viam.components.sensor import Sensor

from viam.resource.registry import Registry, ResourceCreatorRegistration

from .eventManager import eventManager

Registry.register_resource_creator(Sensor.SUBTYPE, eventManager.MODEL, ResourceCreatorRegistration(eventManager.new, eventManager.validate))
