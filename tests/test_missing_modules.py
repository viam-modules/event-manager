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
from src.rules import RuleTime, TimeRange

@pytest.mark.asyncio
class TestMissingModules:
    """Tests to verify functionality when notification modules are not configured"""
    
    async def test_event_without_notification_modules(self):
        """
        Test that events can be processed correctly even if sms_module_name 
        and email_module_name are not defined
        """
        # Create the event manager directly (no config needed)
        manager = eventManager("test_manager")
        manager.logger = MagicMock()
        
        # Set up robot_resources without the notification modules
        manager.robot_resources = {
            'resources': {'test_resource': 'test_value'}
            # Specifically do NOT include sms_module_name or email_module_name
        }
        
        # Create mock dependencies
        manager.deps = {}
        
        # Set active mode
        manager.mode = "active"
        
        # Create a test event with a time rule (doesn't need cameras or other dependencies)
        # Create the rule correctly with a dictionary of time ranges
        rule = RuleTime(type="time", ranges=[{"start_hour": 0, "end_hour": 24}])
        
        event = Event(name="Test Event")
        event.is_triggered = False
        event.rules = [rule]
        event.rule_logic_type = "ANY"
        event.modes = ["active"]
        event.detection_hz = 1
        event.sequence_count_current = 0
        event.trigger_sequence_count = 1
        event.state = "setup"
        
        # Create a stop event to terminate the event check loop
        stop_event = asyncio.Event()
        
        # Run the event check loop for a short time
        task = asyncio.create_task(manager.event_check_loop(event, stop_event))
        
        # Allow the loop to run briefly
        await asyncio.sleep(1)
        
        # Stop the event loop
        stop_event.set()
        await task
        
        # Check that the event was processed
        assert event.state != "setup", "Event should have been processed"
        
        # Make sure no errors were logged related to missing modules
        for call in manager.logger.error.call_args_list:
            args = call[0]
            assert "KeyError" not in str(args), "KeyError was logged"
            assert "sms_module_name" not in str(args), "Error with sms_module_name was logged"
            assert "email_module_name" not in str(args), "Error with email_module_name was logged"
    
    async def test_notification_without_modules(self):
        """
        Test that notifications can be processed without errors when 
        modules are not defined but notifications are configured
        """
        # Create a mock event manager
        manager = eventManager("test_manager")
        manager.logger = MagicMock()
        
        # Create a basic event resources dictionary without notification modules
        event_resources = {
            "_deps": {},
            "resources": {"test_resource": "test_value"}
            # Specifically do NOT include sms_module_name or email_module_name
        }
        
        # Create a test event with notifications
        from src.notificationClass import NotificationSMS, NotificationEmail
        
        event = Event(name="Test Event")
        event.is_triggered = True
        event.triggered_camera = "test-camera"
        event.triggered_label = "test-label"
        
        # Add SMS notification even though module is not configured
        sms_notification = NotificationSMS(to="+1234567890", preset="test")
        
        # Add email notification even though module is not configured
        email_notification = NotificationEmail(to="test@example.com", preset="test")
        
        event.notifications = [sms_notification, email_notification]
        
        # Patch the notify function to test
        with patch('src.notifications.getParam') as mock_get_param:
            mock_get_param.return_value = manager.logger
            
            # Call notify function for each notification
            from src.notifications import notify
            
            # These should not raise exceptions even though modules are missing
            await notify(event, sms_notification, event_resources)
            await notify(event, email_notification, event_resources)
        
        # Verify warning messages were logged about missing modules
        sms_warning_logged = False
        email_warning_logged = False
        
        for call in manager.logger.warning.call_args_list:
            args = call[0]
            if "No SMS module defined" in str(args):
                sms_warning_logged = True
            if "No email module defined" in str(args):
                email_warning_logged = True
        
        assert sms_warning_logged, "Warning about missing SMS module should be logged"
        assert email_warning_logged, "Warning about missing email module should be logged" 