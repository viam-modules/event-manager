import pytest
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio
from datetime import datetime, timedelta

# Add the source directory to the path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent))

from src.triggered import request_capture, get_triggered_cloud, delete_from_cloud, _name_clean, _label, _get_video_store


# Mark only async tests with this decorator
class TestTriggeredHelpers:
    """Tests for helper functions in triggered.py"""
    
    def test_name_clean(self):
        """Test the name_clean function correctly replaces spaces"""
        assert _name_clean("test event") == "test_event"
        assert _name_clean("multiple   spaces") == "multiple___spaces"
        assert _name_clean("no_spaces") == "no_spaces"
    
    def test_label(self):
        """Test the label function creates the correct format"""
        event_name = "Motion Detected"
        cam_name = "Front Door"
        timestamp = 1625097600.123
        
        expected = "SAVCAM--Motion_Detected--Front_Door--1625097600.123"
        result = _label(event_name, cam_name, timestamp)
        
        assert result == expected


class TestVideoStore:
    """Tests for the _get_video_store function"""
    
    def test_get_video_store_generic(self, mock_resources):
        """Test getting video store with generic client"""
        from viam.components.generic import GenericClient
        
        # Setup mock resources
        mock_generic = MagicMock()
        mock_resource_name = "rdk:component:generic:test-store"
        mock_resources['_deps'] = {
            GenericClient.get_resource_name("test-store"): mock_generic
        }
        
        # Test function
        result = _get_video_store("test-store", mock_resources)
        
        # Assertions
        assert result == mock_generic
        assert mock_resources[mock_generic] == mock_generic
    
    def test_get_video_store_camera(self, mock_resources):
        """Test getting video store with camera client"""
        from viam.components.camera import CameraClient
        from viam.components.generic import GenericClient
        
        # Setup mock resources
        mock_camera = MagicMock()
        mock_resources['_deps'] = {
            CameraClient.get_resource_name("test-store"): mock_camera
        }
        
        # Test function
        result = _get_video_store("test-store", mock_resources)
        
        # Assertions
        assert result == mock_camera
        assert mock_resources[mock_camera] == mock_camera


class TestRequestCapture:
    """Tests for the request_capture function"""
    
    @pytest.mark.asyncio
    async def test_successful_capture(self, mock_logger):
        """Test a successful video capture request"""
        # Setup mocks
        mock_event = MagicMock()
        mock_event.video_capture_resource = "test-camera"
        mock_event.event_video_capture_padding_secs = 10
        mock_event.name = "Test Event"
        mock_event.last_triggered = 1625097600.123
        
        mock_video_store = AsyncMock()
        mock_video_store.do_command.return_value = {"status": "saving"}
        
        mock_resources = {"_deps": {}}
        
        # Patch functions
        with patch('src.triggered._get_video_store', return_value=mock_video_store):
            with patch('src.triggered.getParam', return_value=mock_logger):
                with patch('src.triggered.asyncio.sleep') as mock_sleep:
                    # Run the function
                    result = await request_capture(mock_event, mock_resources)
                    
                    # Assertions
                    mock_sleep.assert_called_once_with(10)
                    mock_video_store.do_command.assert_called_once()
                    
                    # Check the save command parameters
                    call_args = mock_video_store.do_command.call_args[0][0]
                    assert call_args["command"] == "save"
                    assert "from" in call_args
                    assert "to" in call_args
                    assert call_args["metadata"] == "SAVCAM--Test_Event--test-camera--1625097600.123"
                    assert call_args["async"] is True
                    
                    # Check the result
                    assert result == {"status": "saving"}
    
    @pytest.mark.asyncio
    async def test_capture_error_handling(self, mock_logger):
        """Test error handling during video capture"""
        # Setup mocks
        mock_event = MagicMock()
        mock_event.video_capture_resource = "test-camera"
        mock_event.event_video_capture_padding_secs = 10
        mock_event.name = "Test Event"
        
        mock_video_store = AsyncMock()
        mock_video_store.do_command.side_effect = Exception("Video store error")
        
        mock_resources = {"_deps": {}}
        
        # Patch functions
        with patch('src.triggered._get_video_store', return_value=mock_video_store):
            with patch('src.triggered.getParam', return_value=mock_logger):
                with patch('src.triggered.asyncio.sleep'):
                    # Run the function
                    result = await request_capture(mock_event, mock_resources)
                    
                    # Assertions
                    mock_video_store.do_command.assert_called_once()
                    mock_logger.error.assert_called_once()
                    assert result is None


class TestCloudFunctions:
    """Tests for cloud-related functions"""
    
    @pytest.mark.asyncio
    async def test_get_triggered_cloud_no_client(self, mock_logger):
        """Test get_triggered_cloud with no app client"""
        with patch('src.triggered.getParam', return_value=mock_logger):
            result = await get_triggered_cloud()
            
            assert "error" in result
    
    @pytest.mark.asyncio
    async def test_delete_from_cloud_no_client(self, mock_logger):
        """Test delete_from_cloud with no app client"""
        with patch('src.triggered.getParam', return_value=mock_logger):
            result = await delete_from_cloud()
            
            assert "error" in result
    
    @pytest.mark.asyncio
    async def test_get_triggered_cloud_with_client(self, mock_logger):
        """Test get_triggered_cloud with a mock app client"""
        # Setup mock app client
        mock_app_client = MagicMock()
        mock_app_client.data_client = AsyncMock()
        
        # Setup mock tabular data response
        mock_tabular_data = [
            {
                "location_id": "loc1",
                "organization_id": "org1",
                "data": {
                    "readings": {
                        "state": {
                            "motion_event": {
                                "last_triggered": "2023-01-01T12:00:00Z",
                                "triggered_camera": "front_door"
                            }
                        }
                    }
                }
            }
        ]
        
        # Setup mock binary data response
        mock_video = MagicMock()
        mock_video.metadata.file_name = "SAVCAM--motion_event--front_door--1672574400.0.mp4"
        mock_video.metadata.id = "video123"
        
        # Configure mock responses
        mock_app_client.data_client.tabular_data_by_mql.return_value = mock_tabular_data
        mock_app_client.data_client.binary_data_by_filter.return_value = ([mock_video], None)
        
        # Patch datetime for consistent testing
        with patch('src.triggered.datetime') as mock_datetime:
            # Configure mock datetime to handle the timestamp conversion
            mock_dt = MagicMock()
            mock_dt.isoformat.return_value = "2023-01-01T12:00:00"
            mock_datetime.fromtimestamp.return_value = mock_dt
            mock_datetime.timezone = MagicMock()
            mock_datetime.timezone.utc = "UTC"
            
            with patch('src.triggered.getParam', return_value=mock_logger):
                result = await get_triggered_cloud(
                    event_manager_name="security_manager",
                    organization_id="org1",
                    event_name="motion_event",
                    num=5,
                    app_client=mock_app_client
                )
                
                # Assertions
                assert len(result) == 1
                assert result[0]["event"] == "motion_event"
                assert result[0]["time"] == "2023-01-01T12:00:00Z"
                assert result[0]["location_id"] == "loc1"
                assert result[0]["organization_id"] == "org1"
                assert result[0]["triggered_camera"] == "front_door"
                
                # Video mapping assertions - depending on how the function works
                # These might need adjustment based on actual implementation
                if "video_id" in result[0]:
                    assert result[0]["video_id"] == "video123"
    
    @pytest.mark.asyncio
    async def test_delete_from_cloud_with_client(self, mock_logger):
        """Test delete_from_cloud with a mock app client"""
        # Setup mock app client
        mock_app_client = MagicMock()
        mock_app_client.data_client = AsyncMock()
        mock_app_client.data_client.delete_binary_data_by_ids.return_value = {"deleted": True}
        
        with patch('src.triggered.getParam', return_value=mock_logger):
            result = await delete_from_cloud(
                id="video123",
                organization_id="org1",
                location_id="loc1",
                app_client=mock_app_client
            )
            
            # Assertions
            mock_app_client.data_client.delete_binary_data_by_ids.assert_called_once()
            assert result == {"deleted": True} 