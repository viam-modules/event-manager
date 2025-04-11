import unittest
import sys
import os
from pathlib import Path

# Add the source directory to the path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent))

from src.notificationClass import NotificationEmail, NotificationSMS, NotificationWebhookGET

class TestNotifications(unittest.TestCase):
    def test_email_notification_initialization(self):
        """Test that NotificationEmail can be properly initialized"""
        email_config = {
            "preset": "Alert",
            "to": "test@example.com",
            "subject": "Test Alert",
            "body": "This is a test alert"
        }
        
        notification = NotificationEmail(**email_config)
        
        self.assertEqual(notification.preset, "Alert")
        self.assertEqual(notification.to, "test@example.com")
        self.assertEqual(notification.subject, "Test Alert")
        self.assertEqual(notification.body, "This is a test alert")
    
    def test_sms_notification_initialization(self):
        """Test that NotificationSMS can be properly initialized"""
        sms_config = {
            "preset": "Alert",
            "to": "+15555555555",
            "body": "Test Alert SMS"
        }
        
        notification = NotificationSMS(**sms_config)
        
        self.assertEqual(notification.preset, "Alert")
        self.assertEqual(notification.to, "+15555555555")
        self.assertEqual(notification.body, "Test Alert SMS")
    
    def test_webhook_notification_initialization(self):
        """Test that NotificationWebhookGET can be properly initialized"""
        webhook_config = {
            "preset": "Alert",
            "url": "https://example.com/webhook",
            "query_params": {"event": "test"}
        }
        
        notification = NotificationWebhookGET(**webhook_config)
        
        self.assertEqual(notification.preset, "Alert")
        self.assertEqual(notification.url, "https://example.com/webhook")
        self.assertEqual(notification.query_params, {"event": "test"})

if __name__ == '__main__':
    unittest.main() 