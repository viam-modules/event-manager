import pytest
import sys
import os
from pathlib import Path
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import time
import re

# Add the source directory to the path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent))

from src.actions import flip_action_status, eval_action, do_action
from src.events import Event
from src.actionClass import Action


class TestActionFunctions:
    """Tests for the action helper functions in actions.py"""
    
    def test_flip_action_status(self):
        """Test that flip_action_status correctly flips all action statuses"""
        # Create an event with multiple actions
        action1 = Action(resource="light", method="turn_on", payload="{}")
        action1.taken = False
        
        action2 = Action(resource="notification", method="send", payload="{}")
        action2.taken = True
        
        action3 = Action(resource="camera", method="record", payload="{}")
        action3.taken = False
        
        event = Event(name="Test Event")
        event.actions = [action1, action2, action3]
        
        # Test flipping from mixed states to True
        flip_action_status(event, True)
        
        # Verify all actions are now True
        for action in event.actions:
            assert action.taken == True
        
        # Test flipping from all True to False
        flip_action_status(event, False)
        
        # Verify all actions are now False
        for action in event.actions:
            assert action.taken == False


@pytest.mark.asyncio
class TestActionEvaluation:
    """Tests for the eval_action and do_action functions"""
    
    async def test_eval_action_already_taken(self):
        """Test that eval_action returns False for actions already taken"""
        # Create an event and action
        event = Event(name="Test Event")
        action = Action(resource="light", method="turn_on", payload="{}")
        action.taken = True  # Action already taken
        
        # Evaluate the action
        result = await eval_action(event, action, "")
        
        # Verify result is False
        assert result == False
    
    async def test_eval_action_response_match(self):
        """Test eval_action with response matching"""
        # Create an event and action with response matching
        event = Event(name="Test Event")
        action = Action(resource="light", method="turn_on", payload="{}")
        action.taken = False
        action.response_match = "confirm|yes"
        action.when_secs = -1  # Add the missing attribute
        
        # Mock logger
        mock_logger = MagicMock()
        with patch('src.actions.getParam', return_value=mock_logger):
            # Test with matching SMS message
            result = await eval_action(event, action, "yes please turn on the light")
            assert result == True
            mock_logger.debug.assert_called_once()
            
            # Reset mock and test with non-matching message
            mock_logger.reset_mock()
            result = await eval_action(event, action, "no don't turn on the light")
            assert result == False
    
    async def test_eval_action_when_secs(self):
        """Test eval_action with when_secs timer"""
        # Create an event and action with when_secs timer
        event = Event(name="Test Event")
        event.last_triggered = time.time() - 300  # Triggered 5 minutes ago
        
        action = Action(resource="notification", method="send", payload="{}")
        action.taken = False
        action.when_secs = 240  # 4 minutes
        
        # Evaluate the action - should return True since more than 4 minutes have passed
        result = await eval_action(event, action, "")
        assert result == True
        
        # Test with insufficient time passed
        action.when_secs = 600  # 10 minutes
        result = await eval_action(event, action, "")
        assert result == False
    
    async def test_eval_action_no_conditions(self):
        """Test eval_action with no conditions"""
        # Create an event and action without conditions
        event = Event(name="Test Event")
        action = Action(resource="light", method="turn_on", payload="{}")
        action.taken = False
        action.response_match = ""
        action.when_secs = -1
        
        # Evaluate the action - should return False as no conditions are met
        result = await eval_action(event, action, "")
        assert result == False
    
    async def test_do_action(self):
        """Test do_action calls the resource method and updates action status"""
        # Create an event and action
        event = Event(name="Test Event")
        action = Action(resource="light", method="turn_on", payload='{"brightness": 100}')
        action.taken = False
        
        # Create mock resources
        resources = {}
        
        # Mock the current time
        current_time = 1000
        
        # Mock the call_method function and time.time
        with patch('src.actions.call_method') as mock_call_method, \
             patch('src.actions.time.time', return_value=current_time):
            
            # Call do_action
            await do_action(event, action, resources)
            
            # Verify call_method was called with the correct parameters
            mock_call_method.assert_called_once_with(
                resources, 
                action.resource, 
                action.method, 
                action.payload, 
                event
            )
            
            # Verify action fields were updated
            assert action.taken == True
            assert action.last_taken == current_time 