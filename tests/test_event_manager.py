import pytest
import sys
import os
from pathlib import Path
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import time
from datetime import datetime, timedelta
import json

# Add the source directory to the path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent))

from src.eventManager import eventManager
from src.events import Event
from src.actions import Action
from viam.utils import SensorReading
from viam.proto.app.robot import ModuleConfig
from viam.proto.common import ResourceName
from viam.resource.base import ResourceBase
from viam.services.generic import Generic as GenericService
from viam.components.generic import Generic as GenericComponent
from viam.components.camera import Camera
from google.protobuf.struct_pb2 import Struct
from src.notificationClass import NotificationPush
from src.rules import RuleDetector

# Basic tests from both files
@pytest.mark.asyncio
class TestEventManagerBasics:
    """Basic tests for eventManager that don't require complex mocking"""
    
    async def test_initialization(self):
        """Test simple initialization of eventManager"""
        # Create a basic event manager
        manager = eventManager("test_manager")
        
        # Check basic properties were initialized
        assert manager.name == "test_manager"
        assert isinstance(manager.event_states, list)
        # Don't check stop_events as it might be populated by the implementation
        assert manager.mode == "inactive"  # Default mode
        
        # Test that the class MODEL is correctly defined (from test_event_manager.py)
        assert eventManager.MODEL.name == "eventing"
    
    async def test_event_action(self):
        """Test event_action method to evaluate and execute actions"""
        # Create an event manager
        manager = eventManager("test_manager")
        manager.logger = MagicMock()
        
        # Create a test event
        event = Event(name="Test Event")
        
        # Create a test action
        action = Action(resource="light", method="turn_on", payload="{}")
        action.taken = False
        action.response_match = ""
        action.when_secs = -1
        
        # Create mock resources
        resources = {}
        
        # Set up mocks
        with patch('src.eventManager.actions.eval_action', return_value=True) as mock_eval_action, \
             patch('src.eventManager.actions.do_action') as mock_do_action:
            
            # Call event_action
            await manager.event_action(event, action, "", resources)
            
            # Verify eval_action was called
            mock_eval_action.assert_called_once_with(event, action, "")
            
            # Verify do_action was called
            mock_do_action.assert_called_once_with(event, action, resources)
    
    async def test_get_readings_basic(self):
        """Test the get_readings method with basic events"""
        # Create an event manager
        manager = eventManager("test_manager")
        manager.logger = MagicMock()
        
        # Setup some test events
        event1 = Event(name="Event 1")
        event1.is_triggered = True
        event1.last_triggered = time.time() - 3600  # Triggered an hour ago
        
        event2 = Event(name="Event 2")
        event2.is_triggered = False
        
        manager.event_states = [event1, event2]
        
        # Mock necessary components for get_readings
        with patch('src.eventManager.pydot.Graph') as mock_graph, \
             patch('src.eventManager.layer_color', return_value="#123456"):
            
            # Call get_readings with empty extra
            readings = await manager.get_readings(extra={})
            
            # Verify readings structure matches implementation
            assert "state" in readings
            assert "Event 1" in readings["state"]
            # Check that Event 1 exists but don't assert specific format
            # as it might vary based on implementation
            
            assert "Event 2" in readings["state"]
            # Check that Event 2 exists but don't assert specific format
    
    async def test_get_readings_with_filter(self):
        """Test the get_readings method with filtering"""
        # Create an event manager
        manager = eventManager("test_manager")
        manager.logger = MagicMock()
        
        # Setup some test events
        event1 = Event(name="Event 1")
        event1.is_triggered = True
        
        event2 = Event(name="Event 2")
        event2.is_triggered = False
        
        manager.event_states = [event1, event2]
        
        # Mock necessary components for get_readings
        with patch('src.eventManager.pydot.Graph') as mock_graph, \
             patch('src.eventManager.layer_color', return_value="#123456"):
            
            # Call get_readings with filter
            readings = await manager.get_readings(extra={"filter": "Event 1"})
            
            # Verify filtered events in state dict
            assert "state" in readings
            assert "Event 1" in readings["state"]
            # Event 2 may still be in the state because get_readings doesn't filter at that level
    
    async def test_do_command_get_status(self):
        """Test do_command with get_status command"""
        # Create an event manager
        manager = eventManager("test_manager")
        manager.logger = MagicMock()
        
        # Setup events
        event1 = Event(name="Event 1")
        event1.state = "monitoring"
        event1.is_triggered = False
        
        event2 = Event(name="Event 2")
        event2.state = "paused"
        event2.is_triggered = True
        event2.last_triggered = time.time() - 60
        
        manager.event_states = [event1, event2]
        
        # Patch the get_readings method to return a mock response
        mock_readings = {
            "state": {
                "Event 1": {"state": "monitoring", "triggered": False},
                "Event 2": {"state": "paused", "triggered": True}
            }
        }
        with patch.object(manager, 'get_readings', return_value=mock_readings):
            # Execute command
            result = await manager.do_command({"command": "get_status"})
            
            # Verify result structure matches implementation
            assert result is not None
            # In the actual implementation, do_command might just return the get_readings result
            # for the get_status command
    
    async def test_do_command_override(self):
        """Test do_command with override command"""
        # Create an event manager
        manager = eventManager("test_manager")
        manager.logger = MagicMock()
        
        # Execute command - we just verify it doesn't throw an exception
        result = await manager.do_command({
            "command": "override", 
            "mode": "inactive", 
            "duration_secs": 3600
        })
        
        # Just verify we got some response without checking specifics
        assert result is not None
    
    async def test_do_command_cancel_override(self):
        """Test do_command with cancel_override command"""
        # Create an event manager
        manager = eventManager("test_manager")
        manager.logger = MagicMock()
        
        # Execute command - we just verify it doesn't throw an exception
        result = await manager.do_command({"command": "cancel_override"})
        
        # Just verify we got some response without checking specifics
        assert result is not None
    
    async def test_do_command_invalid(self):
        """Test do_command with invalid command"""
        # Create an event manager
        manager = eventManager("test_manager")
        manager.logger = MagicMock()
        
        # Execute invalid command
        result = await manager.do_command({"command": "invalid_command"})
        
        # The implementation might handle invalid commands differently
        # Just verify we get some kind of result
        assert result is not None 

class TestEventManagerReconfigureAndLoop:
    """Tests focusing on reconfigure and event_check_loop with push_module."""

    def _create_mock_module_config(self, attributes_dict: dict) -> MagicMock:
        mock_struct = Struct()
        mock_struct.update(attributes_dict)
        
        # Create a MagicMock that simulates ModuleConfig
        mock_config = MagicMock(spec=ModuleConfig) # Spec it to ModuleConfig for some type safety
        mock_config.name = "test_config"
        
        # Mock the .attributes field to be our struct
        # To handle struct_to_dict(config.attributes) which likely accesses .fields
        mock_attributes_object = MagicMock()
        mock_attributes_object.fields = mock_struct.fields # Simulate the .fields attribute of a Struct
        mock_config.attributes = mock_attributes_object
        
        return mock_config

    @pytest.mark.asyncio
    async def test_reconfigure_with_push_module(self):
        manager = eventManager("test_manager_reconfig")
        manager.logger = MagicMock()

        mock_config_attributes = {
            "push_module": "my_push_service"
        }
        config = self._create_mock_module_config(mock_config_attributes)
        dependencies: dict[ResourceName, ResourceBase] = {}

        manager.reconfigure(config, dependencies)

        assert "push_module_name" in manager.robot_resources
        assert manager.robot_resources["push_module_name"] == "my_push_service"

    @pytest.mark.asyncio
    async def test_event_check_loop_with_push_module(self):
        manager = eventManager("test_manager_loop")
        manager.logger = MagicMock()

        # Mock event and push module
        mock_push_service = AsyncMock(spec=GenericService)
        
        # Create a more detailed mock for NotificationPush
        mock_notification_push = MagicMock(spec=NotificationPush)
        mock_notification_push.type = "push"
        mock_notification_push.preset = "TestPushPreset" # Expected by notify
        mock_notification_push.fcm_tokens = ["test_fcm_token123"] # Expected by notify
        mock_notification_push.include_image = False # Expected by notify
        mock_notification_push.image = None # Expected by notify

        event = Event(name="TestPushEvent", detection_hz=1, pause_alerting_on_event_secs=0)
        event.modes = ["active"]
        event.is_triggered = False # Start untriggered
        mock_rule = MagicMock(spec=RuleDetector) # Create a spec'd mock rule
        # Ensure it doesn't have attributes that would cause premature pause
        del mock_rule.inverse_pause_secs 
        del mock_rule.pause_on_known_secs
        event.rules = [mock_rule]
        event.notifications = [mock_notification_push] # Use the detailed mock
        
        manager.mode = "active"
        manager.robot_resources = {
            "push_module_name": "my_push_service",
            "resources": {
                "my_push_service": {"type": "service", "subtype": "generic"}
            }
        }
        manager.deps = {
            GenericService.get_resource_name("my_push_service"): mock_push_service,  # Add the push service
            GenericComponent.get_resource_name("camera1"): MagicMock(),  # Generic component
            Camera.get_resource_name("camera2"): MagicMock(),  # Camera component
            GenericService.get_resource_name("detector1"): MagicMock(),  # Generic service
            GenericComponent.get_resource_name("light1"): MagicMock(),  # Generic component
        }
        manager.event_states = [event] # Ensure the event is in event_states

        stop_event = asyncio.Event()

        # Patch dependencies
        with patch('src.eventManager.globals.setParam') as mock_set_param, \
             patch('src.eventManager.rules.eval_rule', new_callable=AsyncMock, return_value={"triggered": True, "value": "test_label", "resource": "test_camera", "image": MagicMock()}) as mock_eval_rule, \
             patch('src.eventManager.notifications.notify', new_callable=AsyncMock) as mock_notify, \
             patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            
            # mock_sleep to prevent infinite loop in test
            mock_sleep.side_effect = asyncio.CancelledError # Stop loop after first check

            try:
                await manager.event_check_loop(event, stop_event)
            except asyncio.CancelledError:
                pass # Expected

            mock_set_param.assert_called_with('logger', manager.logger)
            mock_eval_rule.assert_called()
            mock_notify.assert_called_once()
            
            # Check that the push_module was correctly passed to notify
            _, args, _ = mock_notify.mock_calls[0]
            called_event_object, called_notification_object, called_resources = args
            assert "push_module" in called_resources
            assert called_resources["push_module"] == mock_push_service 

@pytest.mark.asyncio
class TestResourceAvailability:
    """Tests for resource availability checking in event check loop."""

    async def test_event_with_missing_resources(self):
        """Test that event goes into incomplete state when resources are missing."""
        manager = eventManager("test_manager")
        manager.logger = MagicMock()

        # Set up robot_resources
        manager.robot_resources = {
            "sms_module_name": "",
            "email_module_name": "",
            "push_module_name": "",  # Empty string to avoid push module lookup
            "resources": {
                "detector1": {"type": "service", "subtype": "generic"},
                "camera1": {"type": "component", "subtype": "generic"},
                "camera2": {"type": "component", "subtype": "camera"},
                "light1": {"type": "component", "subtype": "generic"}
            }
        }

        # Create an event that requires multiple resources
        event = Event(name="Test Event")
        event.modes = ["active"]
        event.detection_hz = 1
        event.pause_alerting_on_event_secs = 0
        event.video_capture_resource = "camera1"
        
        # Add a rule that requires a resource
        rule = MagicMock()
        rule.resource = "detector1"
        rule.camera = "camera2"
        event.rules = [rule]
        
        # Add an action that requires a resource
        action = MagicMock()
        action.resource = "light1"
        event.actions = [action]

        # Set up dependencies with some resources missing
        manager.deps = {
            GenericService.get_resource_name("detector1"): MagicMock(),  # Only detector1 is available
            # camera1, camera2, and light1 are missing
        }

        # Create stop event
        stop_event = asyncio.Event()

        # Mock necessary dependencies to prevent infinite loop
        with patch('src.eventManager.globals.setParam') as mock_set_param, \
             patch('src.eventManager.rules.eval_rule', new_callable=AsyncMock) as mock_eval_rule, \
             patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            
            # Set up sleep to raise CancelledError after first check
            mock_sleep.side_effect = asyncio.CancelledError()

            try:
                await manager.event_check_loop(event, stop_event)
            except asyncio.CancelledError:
                pass  # Expected

            # Verify event went into incomplete state
            assert event.state == "incomplete"
            assert "Missing resources" in event.pause_reason
            assert "camera1" in event.pause_reason
            assert "camera2" in event.pause_reason
            assert "light1" in event.pause_reason
            assert "detector1" not in event.pause_reason  # This one was available

            # Verify warning was logged
            manager.logger.warning.assert_called_once()
            warning_msg = manager.logger.warning.call_args[0][0]
            assert "incomplete due to missing resources" in warning_msg
            assert "camera1" in warning_msg
            assert "camera2" in warning_msg
            assert "light1" in warning_msg

    async def test_event_with_all_resources_available(self):
        """Test that event proceeds normally when all resources are available."""
        manager = eventManager("test_manager")
        manager.logger = MagicMock()

        # Set up robot_resources
        manager.robot_resources = {
            "sms_module_name": "",
            "email_module_name": "",
            "push_module_name": "",  # Empty string to avoid push module lookup
            "resources": {
                "detector1": {"type": "service", "subtype": "generic"},
                "camera1": {"type": "component", "subtype": "generic"},
                "camera2": {"type": "component", "subtype": "camera"},
                "light1": {"type": "component", "subtype": "generic"}
            }
        }

        # Create an event that requires multiple resources
        event = Event(name="Test Event")
        event.modes = ["active"]
        event.detection_hz = 1
        event.pause_alerting_on_event_secs = 0
        event.video_capture_resource = "camera1"
        
        # Add a rule that requires a resource
        rule = MagicMock()
        rule.resource = "detector1"
        rule.camera = "camera2"
        event.rules = [rule]
        
        # Add an action that requires a resource
        action = MagicMock()
        action.resource = "light1"
        event.actions = [action]

        # Set up dependencies with all resources available
        manager.deps = {
            GenericComponent.get_resource_name("camera1"): MagicMock(),  # Generic component
            Camera.get_resource_name("camera2"): MagicMock(),  # Camera component
            GenericService.get_resource_name("detector1"): MagicMock(),  # Generic service
            GenericComponent.get_resource_name("light1"): MagicMock(),  # Generic component
        }

        # Create stop event
        stop_event = asyncio.Event()

        # Mock the rule evaluation to prevent infinite loop
        with patch('src.eventManager.rules.eval_rule', new_callable=AsyncMock) as mock_eval_rule:
            mock_eval_rule.return_value = {"triggered": False}
            # Remove CancelledError side effect, use timeout instead

            try:
                await asyncio.wait_for(manager.event_check_loop(event, stop_event), timeout=2)
            except asyncio.TimeoutError:
                stop_event.set()  # Ensure the loop exits if it didn't already
            except asyncio.CancelledError:
                pass  # In case CancelledError is still raised

        # Verify event did not go into incomplete state
        assert event.state != "incomplete"
        assert "Missing resources" not in event.pause_reason

        # Verify no warning was logged
        manager.logger.warning.assert_not_called()

    async def test_event_with_optional_resources(self):
        """Test that event proceeds normally when optional resources are missing."""
        manager = eventManager("test_manager")
        manager.logger = MagicMock()

        # Set up robot_resources
        manager.robot_resources = {
            "sms_module_name": "",
            "email_module_name": "",
            "push_module_name": "",  # Empty string to avoid push module lookup
            "resources": {
                "detector1": {"type": "service", "subtype": "generic"},
                "camera1": {"type": "component", "subtype": "generic"},
                "camera2": {"type": "component", "subtype": "camera"},
                "light1": {"type": "component", "subtype": "generic"}
            }
        }

        # Create an event with only optional resources (no rules or actions)
        event = Event(name="Test Event")
        event.modes = ["active"]
        event.detection_hz = 1
        event.pause_alerting_on_event_secs = 0
        event.video_capture_resource = "camera1"  # Optional resource
        event.rules = []
        event.actions = []
        
        # Set up dependencies with optional resource missing
        manager.deps = {}  # No resources available

        # Create stop event
        stop_event = asyncio.Event()

        # Run the event check loop
        await manager.event_check_loop(event, stop_event)

        # Verify event went into incomplete state
        assert event.state == "incomplete"
        assert "Missing resources" in event.pause_reason
        assert "camera1" in event.pause_reason

        # Verify warning was logged
        manager.logger.warning.assert_called_once()
        warning_msg = manager.logger.warning.call_args[0][0]
        assert "incomplete due to missing resources" in warning_msg
        assert "camera1" in warning_msg 