import pytest
import sys
import os
from pathlib import Path
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from io import BytesIO
import base64
from datetime import datetime, timezone
from PIL import Image

# Add the source directory to the path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent))

from src.notifications import notify, check_sms_response
from src.notificationClass import NotificationEmail, NotificationSMS, NotificationWebhookGET
from src.events import Event

@pytest.fixture
def mock_image():
    """Create a mock PIL image for testing."""
    # Create a small test image
    image = Image.new('RGB', (100, 100), color='red')
    return image

@pytest.fixture
def mock_event():
    """Create a mock event for testing."""
    event = Event(name="Test Event")
    event.triggered_label = "person"
    event.triggered_camera = "front_door"
    return event

@pytest.fixture
def mock_resources():
    """Create mock resources for testing."""
    # Create mock email and SMS modules
    email_module = AsyncMock()
    sms_module = AsyncMock()
    
    # Configure mock responses
    email_module.do_command.return_value = {"status": "sent"}
    sms_module.do_command.return_value = {"status": "sent"}
    
    return {
        "email_module": email_module,
        "sms_module": sms_module
    }

# Class tests converted from unittest format
class TestNotificationClasses:
    """Tests for the notification classes."""
    
    def test_email_notification_initialization(self):
        """Test that NotificationEmail can be properly initialized"""
        email_config = {
            "preset": "Alert",
            "to": "test@example.com",
            "subject": "Test Alert",
            "body": "This is a test alert"
        }
        
        notification = NotificationEmail(**email_config)
        
        assert notification.preset == "Alert"
        assert notification.to == "test@example.com"
        assert notification.subject == "Test Alert"
        assert notification.body == "This is a test alert"
    
    def test_sms_notification_initialization(self):
        """Test that NotificationSMS can be properly initialized"""
        sms_config = {
            "preset": "Alert",
            "to": "+15555555555",
            "body": "Test Alert SMS"
        }
        
        notification = NotificationSMS(**sms_config)
        
        assert notification.preset == "Alert"
        assert notification.to == "+15555555555"
        assert notification.body == "Test Alert SMS"
    
    def test_webhook_notification_initialization(self):
        """Test that NotificationWebhookGET can be properly initialized"""
        webhook_config = {
            "preset": "Alert",
            "url": "https://example.com/webhook",
            "query_params": {"event": "test"}
        }
        
        notification = NotificationWebhookGET(**webhook_config)
        
        assert notification.preset == "Alert"
        assert notification.url == "https://example.com/webhook"
        assert notification.query_params == {"event": "test"}


@pytest.mark.asyncio
class TestNotify:
    """Tests for the notify function."""
    
    async def test_notify_email_with_image(self, mock_event, mock_image, mock_resources):
        """Test sending an email notification with an image."""
        # Create an email notification with an image
        notification = NotificationEmail(
            to="test@example.com",
            preset="Alert",
            include_image=True
        )
        notification.image = mock_image
        
        # Mock the logger
        mock_logger = MagicMock()
        with patch('src.notifications.getParam', return_value=mock_logger):
            # Call notify
            await notify(mock_event, notification, mock_resources)
            
            # Verify the email module was called correctly
            mock_resources["email_module"].do_command.assert_called_once()
            
            # Extract the call arguments
            call_args = mock_resources["email_module"].do_command.call_args[0][0]
            
            # Verify arguments
            assert call_args["command"] == "send"
            assert call_args["to"] == "test@example.com"
            assert call_args["preset"] == "Alert"
            assert "template_vars" in call_args
            assert call_args["template_vars"]["event_name"] == "Test Event"
            assert call_args["template_vars"]["triggered_label"] == "person"
            assert call_args["template_vars"]["triggered_camera"] == "front_door"
            assert "image_base64" in call_args["template_vars"]
            assert "media_mime_type" in call_args["template_vars"]
            # Email should NOT have media_base64 directly in the notification args
            assert "media_base64" not in call_args
    
    async def test_notify_email_without_image(self, mock_event, mock_resources):
        """Test sending an email notification without an image."""
        # Create an email notification without an image
        notification = NotificationEmail(
            to="test@example.com",
            preset="Alert",
            include_image=False
        )
        
        # Mock the logger
        mock_logger = MagicMock()
        with patch('src.notifications.getParam', return_value=mock_logger):
            # Call notify
            await notify(mock_event, notification, mock_resources)
            
            # Verify the email module was called correctly
            mock_resources["email_module"].do_command.assert_called_once()
            
            # Extract the call arguments
            call_args = mock_resources["email_module"].do_command.call_args[0][0]
            
            # Verify arguments
            assert call_args["command"] == "send"
            assert call_args["to"] == "test@example.com"
            assert call_args["preset"] == "Alert"
            assert "template_vars" in call_args
            assert call_args["template_vars"]["event_name"] == "Test Event"
            assert "image_base64" not in call_args["template_vars"]
    
    async def test_notify_sms_with_image(self, mock_event, mock_image, mock_resources):
        """Test sending an SMS notification with an image."""
        # Create an SMS notification with an image
        notification = NotificationSMS(
            to="+15555555555",
            preset="Alert",
            include_image=True
        )
        notification.image = mock_image
        
        # Mock the logger
        mock_logger = MagicMock()
        with patch('src.notifications.getParam', return_value=mock_logger):
            # Call notify
            await notify(mock_event, notification, mock_resources)
            
            # Verify the SMS module was called correctly
            mock_resources["sms_module"].do_command.assert_called_once()
            
            # Extract the call arguments
            call_args = mock_resources["sms_module"].do_command.call_args[0][0]
            
            # Verify arguments
            assert call_args["command"] == "send"
            assert call_args["to"] == "+15555555555"
            assert call_args["preset"] == "Alert"
            assert "template_vars" in call_args
            assert call_args["media_base64"] is not None
            assert call_args["media_mime_type"] == "image/jpeg"
    
    async def test_notify_sms_without_image(self, mock_event, mock_resources):
        """Test sending an SMS notification without an image."""
        # Create an SMS notification without an image
        notification = NotificationSMS(
            to="+15555555555",
            preset="Alert",
            include_image=False
        )
        
        # Mock the logger
        mock_logger = MagicMock()
        with patch('src.notifications.getParam', return_value=mock_logger):
            # Call notify
            await notify(mock_event, notification, mock_resources)
            
            # Verify the SMS module was called correctly
            mock_resources["sms_module"].do_command.assert_called_once()
            
            # Extract the call arguments
            call_args = mock_resources["sms_module"].do_command.call_args[0][0]
            
            # Verify arguments
            assert call_args["command"] == "send"
            assert call_args["to"] == "+15555555555"
            assert call_args["preset"] == "Alert"
            assert "template_vars" in call_args
            assert "media_base64" not in call_args or call_args["media_base64"] is None
    
    async def test_notify_webhook(self, mock_event, mock_resources):
        """Test sending a webhook notification."""
        # Create a webhook notification
        notification = NotificationWebhookGET(
            url="https://example.com/webhook"
        )
        
        # Mock the logger and urllib
        mock_logger = MagicMock()
        mock_url_open = MagicMock()
        mock_url_open.read.return_value = b"Success"
        
        with patch('src.notifications.getParam', return_value=mock_logger), \
             patch('urllib.request.urlopen', return_value=mock_url_open):
            # Call notify
            result = await notify(mock_event, notification, mock_resources)
            
            # Verify urllib was called correctly
            import urllib.request
            urllib.request.urlopen.assert_called_once_with("https://example.com/webhook")
    
    async def test_notify_missing_email_module(self, mock_event, mock_resources):
        """Test handling when email module is missing."""
        # Create an email notification
        notification = NotificationEmail(
            to="test@example.com",
            preset="Alert"
        )
        
        # Remove the email module from resources
        mock_resources_without_email = {k: v for k, v in mock_resources.items() if k != "email_module"}
        
        # Mock the logger
        mock_logger = MagicMock()
        with patch('src.notifications.getParam', return_value=mock_logger):
            # Call notify
            await notify(mock_event, notification, mock_resources_without_email)
            
            # Verify warning was logged
            mock_logger.warning.assert_called_once()
    
    async def test_notify_missing_sms_module(self, mock_event, mock_resources):
        """Test handling when SMS module is missing."""
        # Create an SMS notification
        notification = NotificationSMS(
            to="+15555555555",
            preset="Alert",
            include_image=False  # Don't include image
        )
        
        # Remove the SMS module from resources
        mock_resources_without_sms = {k: v for k, v in mock_resources.items() if k != "sms_module"}
        
        # Mock the logger
        mock_logger = MagicMock()
        with patch('src.notifications.getParam', return_value=mock_logger):
            # Call notify
            await notify(mock_event, notification, mock_resources_without_sms)
            
            # Verify warning was logged
            mock_logger.warning.assert_called_once()
    
    async def test_notify_error_handling(self, mock_event, mock_image, mock_resources):
        """Test error handling in notify."""
        # Create an email notification
        notification = NotificationEmail(
            to="test@example.com",
            preset="Alert",
            include_image=True
        )
        notification.image = mock_image
        
        # Configure email module to return an error
        mock_resources["email_module"].do_command.return_value = {"error": "Failed to send email"}
        
        # Mock the logger
        mock_logger = MagicMock()
        with patch('src.notifications.getParam', return_value=mock_logger):
            # Call notify
            await notify(mock_event, notification, mock_resources)
            
            # Verify error was logged
            mock_logger.error.assert_called_once()
    
    async def test_notify_exception_handling(self, mock_event, mock_image, mock_resources):
        """Test exception handling in notify."""
        # Create an email notification
        notification = NotificationEmail(
            to="test@example.com",
            preset="Alert",
            include_image=True
        )
        notification.image = mock_image
        
        # Configure email module to raise an exception
        mock_resources["email_module"].do_command.side_effect = Exception("Test error")
        
        # Mock the logger
        mock_logger = MagicMock()
        with patch('src.notifications.getParam', return_value=mock_logger):
            # Call notify
            await notify(mock_event, notification, mock_resources)
            
            # Verify error was logged
            mock_logger.error.assert_called_once()


@pytest.mark.asyncio
class TestCheckSmsResponse:
    """Tests for the check_sms_response function."""
    
    async def test_check_sms_response_with_messages(self, mock_resources):
        """Test checking for SMS responses with messages."""
        # Create a list of notifications including an SMS
        notifications = [
            NotificationSMS(to="+15555555555", preset="Alert")
        ]
        
        # Mock time
        since_time = 1625097600  # 2021-07-01T00:00:00Z
        
        # Configure SMS module to return messages
        mock_resources["sms_module"].do_command.return_value = {
            "messages": [
                {"body": "YES", "from": "+15555555555", "time": "01/07/2021 00:05:00"}
            ]
        }
        
        # Mock the logger
        mock_logger = MagicMock()
        with patch('src.notifications.getParam', return_value=mock_logger), \
             patch('src.notifications.datetime') as mock_datetime:
            # Configure mock datetime
            mock_dt = MagicMock()
            mock_dt.strftime.return_value = "01/07/2021 00:00:00"
            mock_datetime.fromtimestamp.return_value = mock_dt
            mock_datetime.timezone = timezone
            
            # Call check_sms_response
            result = await check_sms_response(notifications, since_time, mock_resources)
            
            # Verify result
            assert result == "YES"
            
            # Verify SMS module was called correctly
            mock_resources["sms_module"].do_command.assert_called_once()
            call_args = mock_resources["sms_module"].do_command.call_args[0][0]
            assert call_args["command"] == "get"
            assert call_args["from"] == "+15555555555"
    
    async def test_check_sms_response_without_messages(self, mock_resources):
        """Test checking for SMS responses without messages."""
        # Create a list of notifications including an SMS
        notifications = [
            NotificationSMS(to="+15555555555", preset="Alert")
        ]
        
        # Mock time
        since_time = 1625097600  # 2021-07-01T00:00:00Z
        
        # Configure SMS module to return no messages
        mock_resources["sms_module"].do_command.return_value = {"messages": []}
        
        # Mock the logger
        mock_logger = MagicMock()
        with patch('src.notifications.getParam', return_value=mock_logger), \
             patch('src.notifications.datetime') as mock_datetime:
            # Configure mock datetime
            mock_dt = MagicMock()
            mock_dt.strftime.return_value = "01/07/2021 00:00:00"
            mock_datetime.fromtimestamp.return_value = mock_dt
            mock_datetime.timezone = timezone
            
            # Call check_sms_response
            result = await check_sms_response(notifications, since_time, mock_resources)
            
            # Verify result
            assert result == ""
    
    async def test_check_sms_response_without_sms_notifications(self, mock_resources):
        """Test checking for SMS responses without SMS notifications."""
        # Create a list of notifications without SMS
        notifications = [
            NotificationEmail(to="test@example.com", preset="Alert")
        ]
        
        # Mock time
        since_time = 1625097600  # 2021-07-01T00:00:00Z
        
        # Mock the logger
        mock_logger = MagicMock()
        with patch('src.notifications.getParam', return_value=mock_logger), \
             patch('src.notifications.datetime') as mock_datetime:
            # Configure mock datetime
            mock_dt = MagicMock()
            mock_dt.strftime.return_value = "01/07/2021 00:00:00"
            mock_datetime.fromtimestamp.return_value = mock_dt
            mock_datetime.timezone = timezone
            
            # Call check_sms_response
            result = await check_sms_response(notifications, since_time, mock_resources)
            
            # Verify result
            assert result == ""
            
            # Verify SMS module was not called
            mock_resources["sms_module"].do_command.assert_not_called() 