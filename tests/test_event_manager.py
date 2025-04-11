import unittest
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add the source directory to the path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent))

from src.eventManager import eventManager, Modes

class TestEventManager(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.event_manager = eventManager("test_event_manager")
        
    def test_initialization(self):
        """Test basic initialization of eventManager"""
        self.assertEqual(self.event_manager.name, "test_event_manager")
        self.assertEqual(self.event_manager.mode, "inactive")
        self.assertEqual(len(self.event_manager.event_states), 0)
        
        # Test that the class MODEL is correctly defined
        self.assertEqual(eventManager.MODEL.name, "eventing")

if __name__ == '__main__':
    unittest.main() 