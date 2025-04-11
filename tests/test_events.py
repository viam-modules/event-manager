import unittest
import sys
import os
from pathlib import Path

# Add the source directory to the path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent))

from src.events import Event
from src.notificationClass import NotificationEmail, NotificationSMS, NotificationWebhookGET
from src.rules import RuleDetector

class TestEvent(unittest.TestCase):
    def test_event_initialization(self):
        """Test that an Event can be properly initialized"""
        event_config = {
            "name": "Test Event",
            "capture_video": True,
            "video_capture_resource": "camera1",
            "modes": ["active", "inactive"],
            "rules": [
                {
                    "type": "detection",
                    "camera": "camera1",
                    "labels": ["person"],
                    "confidence": 0.7
                }
            ],
            "notifications": [
                {
                    "type": "email",
                    "preset": "Alert",
                    "to": ["test@example.com"]
                }
            ]
        }
        
        event = Event(**event_config)
        
        # Test basic properties
        self.assertEqual(event.name, "Test Event")
        self.assertEqual(event.capture_video, True)
        self.assertEqual(event.video_capture_resource, "camera1")
        self.assertEqual(event.modes, ["active", "inactive"])
        
        # Test rules initialization
        self.assertEqual(len(event.rules), 1)
        self.assertIsInstance(event.rules[0], RuleDetector)
        self.assertEqual(event.rules[0].camera, "camera1")
        self.assertEqual(event.rules[0].labels, ["person"])
        self.assertEqual(event.rules[0].confidence, 0.7)
        
        # Test notifications initialization
        self.assertEqual(len(event.notifications), 1)
        self.assertIsInstance(event.notifications[0], NotificationEmail)
        self.assertEqual(event.notifications[0].to, "test@example.com")
        self.assertEqual(event.notifications[0].preset, "Alert")
        
    def test_default_values(self):
        """Test that default values are set correctly"""
        event = Event(name="Minimal Event")
        
        self.assertEqual(event.name, "Minimal Event")
        self.assertEqual(event.state, "paused")
        self.assertEqual(event.is_triggered, False)
        self.assertEqual(event.rule_logic_type, "AND")
        self.assertEqual(event.trigger_sequence_count, 1)
        self.assertEqual(event.sequence_count_current, 0)

if __name__ == '__main__':
    unittest.main() 