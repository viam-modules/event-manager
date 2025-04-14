import pytest
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import time
from datetime import datetime, timezone
from viam.errors import NoCaptureToStoreError

# Add the source directory to the path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent))

from src.eventManager import eventManager
from src.events import Event
from src.triggered import _label


@pytest.mark.asyncio
class TestTimestampWriting:
    """Tests to verify consistent timestamp handling between components"""
    
    async def test_timestamp_format_consistency(self):
        """
        Test that timestamps are consistently formatted between eventManager.get_readings() 
        and triggered._label() to ensure they can be matched later
        """
        # Create event manager with mock logger
        manager = eventManager("test_manager")
        manager.logger = MagicMock()
        
        # Create test event with a specific timestamp
        # Use a timestamp with millisecond precision
        original_timestamp = 1650123456.789  # A timestamp with milliseconds
        
        event = Event(name="Test Event")
        event.is_triggered = True
        event.last_triggered = original_timestamp
        event.state = "triggered"
        event.triggered_camera = "test-camera"
        event.triggered_label = "person_1"
        
        # Add event to manager
        manager.event_states = [event]
        
        # Get readings from event manager (simulating what's stored in data manager)
        readings = await manager.get_readings()
        
        # Extract the formatted timestamp from readings
        readings_timestamp = readings["state"]["Test Event"]["last_triggered"]
        
        # Generate a video label using the triggered._label function
        video_label = _label("Test Event", "test-camera", original_timestamp)
        
        # Extract timestamp from video label
        video_timestamp_str = video_label.split('--')[3]
        
        # Print both for debugging
        print(f"Original timestamp: {original_timestamp}")
        print(f"Readings timestamp: {readings_timestamp}")
        print(f"Video label: {video_label}")
        
        # Convert video timestamp string back to ISO format as get_triggered_cloud would
        video_dt = datetime.fromtimestamp(int(float(video_timestamp_str)), timezone.utc)
        video_iso = video_dt.isoformat() + 'Z'
        
        # Get the expected format by manually constructing it the same way get_readings does
        expected_dt = datetime.fromtimestamp(int(original_timestamp), timezone.utc)
        expected_iso = expected_dt.isoformat() + 'Z'
        
        # Check consistency
        assert expected_iso == video_iso, "Integer timestamp conversion is inconsistent between components"
        
        # Verify readings timestamp format matches our expected format
        assert readings_timestamp == expected_iso, "get_readings() timestamp format doesn't match expected format"
    
    async def test_dm_sent_status_tracking(self):
        """
        Test that dm_sent_status is properly updated to track sent events,
        which is critical for preventing duplicates
        """
        # Create event manager with mock
        manager = eventManager("test_manager")
        manager.logger = MagicMock()
        manager.dm_sent_status = {}
        
        # Create two test events
        event1 = Event(name="Event 1")
        event1.is_triggered = True
        event1.last_triggered = 1650123456.0
        event1.state = "triggered"
        
        event2 = Event(name="Event 2")
        event2.is_triggered = True
        event2.last_triggered = 1650123457.0
        event2.state = "triggered"
        
        # Add events to manager
        manager.event_states = [event1, event2]
        
        # Mock from_dm_from_extra to simulate data manager capture
        with patch('src.eventManager.from_dm_from_extra', return_value=True):
            # Get readings from event manager
            readings = await manager.get_readings(extra={})
            
            # Verify dm_sent_status was updated correctly for both events
            assert "Event 1" in manager.dm_sent_status
            assert manager.dm_sent_status["Event 1"] == event1.last_triggered
            
            assert "Event 2" in manager.dm_sent_status
            assert manager.dm_sent_status["Event 2"] == event2.last_triggered
            
            # Now call get_readings again - it should raise NoCaptureToStoreError
            # since all events have been processed already
            with pytest.raises(NoCaptureToStoreError):
                await manager.get_readings(extra={})
            
            # Change event1's last_triggered to simulate a new trigger
            event1.last_triggered = 1650123458.0
            
            # Call get_readings again - should work now with the updated timestamp
            readings3 = await manager.get_readings(extra={})
            
            # Should only include Event 1 now with the new timestamp
            assert len(readings3["state"]) == 1
            assert "Event 1" in readings3["state"]
            
            # Verify dm_sent_status was updated with new timestamp
            assert manager.dm_sent_status["Event 1"] == event1.last_triggered 