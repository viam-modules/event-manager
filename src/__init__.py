"""
This file registers the model with the Python SDK.
"""

from viam.services.generic import Generic
from viam.resource.registry import Registry, ResourceCreatorRegistration

from .eventManager import eventManager

Registry.register_resource_creator(Generic.SUBTYPE, eventManager.MODEL, ResourceCreatorRegistration(eventManager.new, eventManager.validate))
