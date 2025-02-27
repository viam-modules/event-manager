#!/usr/bin/env python3
import asyncio
import sys

from viam.module.module import Module
from viam.components.sensor import Sensor
from viam.resource.registry import Registry, ResourceCreatorRegistration

from src.eventManager import eventManager

async def main():
    """This function creates and starts a new module, after adding all desired resources.
    Resources must be pre-registered. For an example, see the `__init__.py` file.
    """

    Registry.register_resource_creator(Sensor.API, eventManager.MODEL, ResourceCreatorRegistration(eventManager.new, eventManager.validate))

    module = Module.from_args()
    module.add_model_from_registry(Sensor.API, eventManager.MODEL)

    await module.start()

if __name__ == "__main__":
    asyncio.run(main())
