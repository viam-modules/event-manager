import pytest
import sys
import os
from pathlib import Path

# Add the source directory to the path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent))

from src.notificationClass import NotificationEmail, NotificationSMS, NotificationWebhookGET

def test_email_notification():
    """Test that NotificationEmail can be properly initialized with pytest"""
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

def test_sms_notification():
    """Test that NotificationSMS can be properly initialized with pytest"""
    sms_config = {
        "preset": "Alert",
        "to": "+15555555555",
        "body": "Test Alert SMS"
    }
    
    notification = NotificationSMS(**sms_config)
    
    assert notification.preset == "Alert"
    assert notification.to == "+15555555555"
    assert notification.body == "Test Alert SMS"

def test_webhook_notification():
    """Test that NotificationWebhookGET can be properly initialized with pytest"""
    webhook_config = {
        "preset": "Alert",
        "url": "https://example.com/webhook",
        "query_params": {"event": "test"}
    }
    
    notification = NotificationWebhookGET(**webhook_config)
    
    assert notification.preset == "Alert"
    assert notification.url == "https://example.com/webhook"
    assert notification.query_params == {"event": "test"} 