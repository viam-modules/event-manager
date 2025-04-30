import pytest
import sys
import os
import tempfile
import sqlite3
from pathlib import Path
import asyncio
from unittest.mock import MagicMock, patch
import time
import shutil
import pickle

# Add the source directory to the path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent))

from src.eventManager import eventManager
from src.events import Event
from src.rules import RuleTime


@pytest.mark.asyncio
class TestStatePersistence:
    """Tests for the state persistence functionality."""
    
    @pytest.fixture
    def temp_db_dir(self):
        """Create a temporary directory for the test database."""
        test_dir = tempfile.mkdtemp()
        yield test_dir
        # Clean up after test
        shutil.rmtree(test_dir)
    
    async def test_state_persistence_disabled_by_default(self):
        """Test that state persistence is disabled by default."""
        manager = eventManager("test_manager")
        manager.logger = MagicMock()
        
        # Verify defaults
        assert manager.back_state_to_disk is False
        assert manager.db_path == ""
    
    async def test_save_and_restore_event_states(self, temp_db_dir):
        """Test saving and restoring event states."""
        # Create a manager with state persistence enabled
        manager = eventManager("test_manager")
        manager.logger = MagicMock()
        manager.back_state_to_disk = True
        manager.db_path = os.path.join(temp_db_dir, "test_events.db")
        manager._init_db()
        
        # Create a test event
        event1 = Event(name="Test Event 1")
        event1.is_triggered = True
        event1.last_triggered = 1650123456.0
        event1.state = "triggered"
        event1.triggered_camera = "camera1"
        event1.triggered_label = "person"
        
        event2 = Event(name="Test Event 2")
        event2.is_triggered = False
        event2.state = "monitoring"
        
        # Add events to manager
        manager.event_states = [event1, event2]
        
        # Save states
        manager._save_event_states()
        
        # Verify database exists
        assert os.path.exists(manager.db_path)
        
        # Create a new manager to test restoration
        new_manager = eventManager("test_manager")
        new_manager.logger = MagicMock()
        new_manager.back_state_to_disk = True
        new_manager.db_path = manager.db_path
        
        # Create fresh events with different states
        fresh_event1 = Event(name="Test Event 1")
        fresh_event1.is_triggered = False
        fresh_event1.state = "setup"
        
        fresh_event2 = Event(name="Test Event 2")
        fresh_event2.is_triggered = False
        fresh_event2.state = "setup"
        
        # Add fresh events to new manager
        new_manager.event_states = [fresh_event1, fresh_event2]
        
        # Restore states
        new_manager._restore_event_states()
        
        # Verify states were restored
        assert new_manager.event_states[0].name == "Test Event 1"
        assert new_manager.event_states[0].is_triggered is True
        assert new_manager.event_states[0].state == "triggered"
        assert new_manager.event_states[0].triggered_camera == "camera1"
        assert new_manager.event_states[0].triggered_label == "person"
        
        assert new_manager.event_states[1].name == "Test Event 2"
        assert new_manager.event_states[1].is_triggered is False
        assert new_manager.event_states[1].state == "monitoring"
    
    async def test_state_persistence_skip_missing_events(self, temp_db_dir):
        """Test that restoration skips events not in current configuration."""
        # Create a manager with state persistence enabled
        manager = eventManager("test_manager")
        manager.logger = MagicMock()
        manager.back_state_to_disk = True
        manager.db_path = os.path.join(temp_db_dir, "test_events.db")
        manager._init_db()
        
        # Create test events
        event1 = Event(name="Event 1")
        event1.is_triggered = True
        event1.state = "triggered"
        
        event2 = Event(name="Event 2")
        event2.is_triggered = False
        event2.state = "monitoring"
        
        # Add events to manager
        manager.event_states = [event1, event2]
        
        # Save states
        manager._save_event_states()
        
        # Create a new manager with different events
        new_manager = eventManager("test_manager")
        new_manager.logger = MagicMock()
        new_manager.back_state_to_disk = True
        new_manager.db_path = manager.db_path
        
        # Create fresh events with one different name
        fresh_event1 = Event(name="Event 1")  # Same name, should restore
        fresh_event1.is_triggered = False
        fresh_event1.state = "setup"
        
        fresh_event3 = Event(name="Event 3")  # Different name, should not find state
        fresh_event3.is_triggered = False
        fresh_event3.state = "setup"
        
        # Add fresh events to new manager
        new_manager.event_states = [fresh_event1, fresh_event3]
        
        # Restore states
        new_manager._restore_event_states()
        
        # Verify Event 1 was restored
        assert new_manager.event_states[0].name == "Event 1"
        assert new_manager.event_states[0].is_triggered is True
        assert new_manager.event_states[0].state == "triggered"
        
        # Verify Event 3 was not changed (no saved state)
        assert new_manager.event_states[1].name == "Event 3"
        assert new_manager.event_states[1].is_triggered is False
        assert new_manager.event_states[1].state == "setup"
        
    async def test_error_handling_during_restore(self, temp_db_dir):
        """Test error handling during state restoration."""
        # Create a manager with state persistence enabled
        manager = eventManager("test_manager")
        manager.logger = MagicMock()
        manager.back_state_to_disk = True
        manager.db_path = os.path.join(temp_db_dir, "test_events.db")
        
        # Create invalid database structure
        conn = sqlite3.connect(manager.db_path)
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE event_states (id INTEGER PRIMARY KEY, event_name TEXT, invalid_data TEXT)')
        cursor.execute('INSERT INTO event_states (event_name, invalid_data) VALUES (?, ?)', 
                      ('Test Event', 'not-pickle-data'))
        conn.commit()
        conn.close()
        
        # Create test events
        event = Event(name="Test Event")
        event.is_triggered = False
        event.state = "setup"
        
        # Add event to manager
        manager.event_states = [event]
        
        # Try to restore states - should handle error gracefully
        manager._restore_event_states()
        
        # Verify error was logged
        assert manager.logger.error.called
        
        # Verify original state was preserved
        assert manager.event_states[0].name == "Test Event"
        assert manager.event_states[0].is_triggered is False
        assert manager.event_states[0].state == "setup"
        
    async def test_rule_reset_feature(self):
        """Test the rule_reset feature that prevents retriggering until rules evaluate as false."""
        # Set up the event
        event = Event(name="Test Event")
        event.require_rule_reset = True
        event.rule_reset_count = 2
        event.is_triggered = True
        event.rule_reset_counter = 0
        
        # Mock rule results
        mock_rule_results = [{"triggered": False}]
        
        # First false evaluation (1/2)
        # This should increment the counter but not reset triggered state
        event = await self._simulate_rule_eval(event, mock_rule_results, False)
        assert event.is_triggered is True  # Still triggered
        assert event.rule_reset_counter == 1  # Counter incremented
        
        # Second false evaluation (2/2)
        # This should reset the triggered state since we reached rule_reset_count
        event = await self._simulate_rule_eval(event, mock_rule_results, False)
        assert event.is_triggered is False  # Not triggered anymore
        assert event.rule_reset_counter == 0  # Counter reset
        
        # True evaluation - should trigger again
        mock_rule_results = [{"triggered": True}]
        event = await self._simulate_rule_eval(event, mock_rule_results, True)
        assert event.is_triggered is True  # Triggered again
        assert event.rule_reset_counter == 0  # Counter still reset
        
    async def _simulate_rule_eval(self, event, rule_results, rules_triggered):
        """Helper method to simulate rule evaluation logic from eventManager."""
        # Simplified version of the logic from eventManager.py
        if event.is_triggered and event.require_rule_reset:
            if not rules_triggered:
                event.rule_reset_counter += 1
                if event.rule_reset_counter >= event.rule_reset_count:
                    event.is_triggered = False
                    event.rule_reset_counter = 0
            else:
                event.rule_reset_counter = 0
                
        if rules_triggered and not event.is_triggered:
            event.is_triggered = True
            event.last_triggered = time.time()
            event.rule_reset_counter = 0
            
        return event
        
    async def test_rule_reset_state_persistence(self, temp_db_dir):
        """Test that rule reset state is properly saved and restored."""
        # Create a manager with state persistence enabled
        manager = eventManager("test_manager")
        manager.logger = MagicMock()
        manager.back_state_to_disk = True
        manager.db_path = os.path.join(temp_db_dir, "test_events.db")
        manager._init_db()
        
        # Create a test event with rule reset enabled
        event = Event(name="Test Event")
        event.require_rule_reset = True
        event.rule_reset_count = 3
        event.is_triggered = True
        event.rule_reset_counter = 2  # Simulate that we're almost at the reset count
        event.state = "triggered"
        
        # Add event to manager
        manager.event_states = [event]
        
        # Save states
        manager._save_event_states()
        
        # Verify database exists
        assert os.path.exists(manager.db_path)
        
        # Create a new manager to test restoration
        new_manager = eventManager("test_manager")
        new_manager.logger = MagicMock()
        new_manager.back_state_to_disk = True
        new_manager.db_path = manager.db_path
        
        # Create fresh event with default rule reset state
        fresh_event = Event(name="Test Event")
        fresh_event.is_triggered = False
        fresh_event.state = "setup"
        fresh_event.require_rule_reset = False  # Default value
        fresh_event.rule_reset_counter = 0      # Default value
        
        # Add fresh event to new manager
        new_manager.event_states = [fresh_event]
        
        # Restore states
        new_manager._restore_event_states()
        
        # Verify rule reset state was restored
        restored_event = new_manager.event_states[0]
        assert restored_event.name == "Test Event"
        assert restored_event.is_triggered is True
        assert restored_event.state == "triggered"
        assert restored_event.require_rule_reset is True
        assert restored_event.rule_reset_count == 3
        assert restored_event.rule_reset_counter == 2 