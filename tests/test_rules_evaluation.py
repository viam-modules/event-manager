import unittest
import sys
import os
from pathlib import Path
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import re
from datetime import datetime

# Add the source directory to the path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent))

from src.rules import (
    RuleDetector, RuleClassifier, RuleTime, RuleTracker, RuleCall, TimeRange,
    eval_rule, logical_trigger, get_value_by_dot_notation
)

class TestRuleTrackerInitialization(unittest.TestCase):
    def test_rule_tracker_initialization(self):
        """Test that a RuleTracker can be properly initialized"""
        rule_config = {
            "camera": "camera1",
            "tracker": "tracker1",
            "inverse_pause_secs": 60,
            "pause_on_known_secs": 300
        }
        
        rule = RuleTracker(**rule_config)
        
        self.assertEqual(rule.camera, "camera1")
        self.assertEqual(rule.tracker, "tracker1")
        self.assertEqual(rule.inverse_pause_secs, 60)
        self.assertEqual(rule.pause_on_known_secs, 300)
    
    def test_rule_call_initialization(self):
        """Test that a RuleCall can be properly initialized"""
        rule_config = {
            "resource": "sensor1",
            "method": "get_readings",
            "payload": '{"parameter": "value"}',
            "result_path": "readings.temperature",
            "result_function": "len",
            "result_operator": "gt",
            "result_value": 25,
            "inverse_pause_secs": 30
        }
        
        rule = RuleCall(**rule_config)
        
        self.assertEqual(rule.resource, "sensor1")
        self.assertEqual(rule.method, "get_readings")
        self.assertEqual(rule.payload, '{"parameter": "value"}')
        self.assertEqual(rule.result_path, "readings.temperature")
        self.assertEqual(rule.result_function, "len")
        self.assertEqual(rule.result_operator, "gt")
        self.assertEqual(rule.result_value, 25)
        self.assertEqual(rule.inverse_pause_secs, 30)

class TestGetValueByDotNotation(unittest.TestCase):
    def test_get_simple_value(self):
        """Test getting a simple value from a dict using dot notation"""
        data = {"key": "value"}
        result = get_value_by_dot_notation(data, "key")
        self.assertEqual(result, "value")
    
    def test_get_nested_value(self):
        """Test getting a nested value from a dict using dot notation"""
        data = {"parent": {"child": "value"}}
        result = get_value_by_dot_notation(data, "parent.child")
        self.assertEqual(result, "value")
    
    def test_get_deeply_nested_value(self):
        """Test getting a deeply nested value from a dict using dot notation"""
        data = {"level1": {"level2": {"level3": "value"}}}
        result = get_value_by_dot_notation(data, "level1.level2.level3")
        self.assertEqual(result, "value")
    
    def test_nonexistent_key(self):
        """Test getting a nonexistent key returns None"""
        data = {"key": "value"}
        result = get_value_by_dot_notation(data, "nonexistent")
        self.assertIsNone(result)
    
    def test_nonexistent_nested_key(self):
        """Test getting a nonexistent nested key returns None"""
        data = {"parent": {"child": "value"}}
        result = get_value_by_dot_notation(data, "parent.nonexistent")
        self.assertIsNone(result)
    
    def test_invalid_parent_key(self):
        """Test getting a nested key with an invalid parent returns None"""
        data = {"key": "value"}
        result = get_value_by_dot_notation(data, "nonexistent.child")
        self.assertIsNone(result)

class TestLogicalTrigger(unittest.TestCase):
    def test_logical_trigger_and_all_true(self):
        """Test logical_trigger with AND and all values true"""
        with patch('src.rules.logic.AND') as mock_and:
            mock_and.return_value = True
            result = logical_trigger("AND", [True, True, True])
            mock_and.assert_called_once_with([True, True, True])
            self.assertTrue(result)
    
    def test_logical_trigger_and_one_false(self):
        """Test logical_trigger with AND and one value false"""
        with patch('src.rules.logic.AND') as mock_and:
            mock_and.return_value = False
            result = logical_trigger("AND", [True, False, True])
            mock_and.assert_called_once_with([True, False, True])
            self.assertFalse(result)
    
    def test_logical_trigger_or_one_true(self):
        """Test logical_trigger with OR and one value true"""
        with patch('src.rules.logic.OR') as mock_or:
            mock_or.return_value = True
            result = logical_trigger("OR", [False, True, False])
            mock_or.assert_called_once_with([False, True, False])
            self.assertTrue(result)
    
    def test_logical_trigger_or_all_false(self):
        """Test logical_trigger with OR and all values false"""
        with patch('src.rules.logic.OR') as mock_or:
            mock_or.return_value = False
            result = logical_trigger("OR", [False, False, False])
            mock_or.assert_called_once_with([False, False, False])
            self.assertFalse(result)

class TestRuleEvaluation(unittest.IsolatedAsyncioTestCase):
    async def test_time_rule_evaluation_matching(self):
        """Test evaluating a time rule that matches current time"""
        rule = RuleTime()
        rule.ranges = [
            TimeRange(start_hour=0, end_hour=24)  # All day
        ]
        
        with patch('src.rules.datetime') as mock_datetime:
            # Mock datetime.now to return a specific time
            mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)
            mock_logger = MagicMock()
            
            with patch('src.rules.getParam', return_value=mock_logger):
                result = await eval_rule(rule, {})
            
            self.assertTrue(result["triggered"])
    
    async def test_time_rule_evaluation_not_matching(self):
        """Test evaluating a time rule that doesn't match current time"""
        rule = RuleTime()
        rule.ranges = [
            TimeRange(start_hour=13, end_hour=15)  # 1 PM to 3 PM
        ]
        
        with patch('src.rules.datetime') as mock_datetime:
            # Mock datetime.now to return a specific time outside the range
            mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)
            mock_logger = MagicMock()
            
            with patch('src.rules.getParam', return_value=mock_logger):
                result = await eval_rule(rule, {})
            
            self.assertFalse(result["triggered"])
    
    async def test_detector_rule_evaluation_matching(self):
        """Test evaluating a detector rule with matching detections"""
        rule = RuleDetector()
        rule.type = "detection"
        rule.detector = "test_detector"
        rule.camera = "test_camera"
        rule.confidence_pct = 0.7
        rule.class_regex = "person"
        
        # Mock dependencies
        mock_detection = MagicMock()
        mock_detection.class_name = "person"
        mock_detection.confidence = 0.8
        
        mock_all = MagicMock()
        mock_all.detections = [mock_detection]
        
        mock_detector = AsyncMock()
        mock_detector.capture_all_from_camera.return_value = mock_all
        
        mock_logger = MagicMock()
        mock_resources = {"_deps": {}}
        
        # Create a mock PIL image
        mock_pil_image = MagicMock()
        
        with patch('src.rules.getParam', return_value=mock_logger):
            with patch('src.rules._get_vision_service', return_value=mock_detector):
                with patch('src.rules.viam_to_pil_image', return_value=mock_pil_image):
                    result = await eval_rule(rule, mock_resources)
                    
                    self.assertTrue(result["triggered"])
                    mock_detector.capture_all_from_camera.assert_called_once_with(
                        "test_camera", return_detections=True, return_image=True
                    )
    
    async def test_detector_rule_evaluation_not_matching_confidence(self):
        """Test evaluating a detector rule with detection below confidence threshold"""
        rule = RuleDetector()
        rule.type = "detection"
        rule.detector = "test_detector"
        rule.camera = "test_camera"
        rule.confidence_pct = 0.7
        rule.class_regex = "person"
        
        # Mock dependencies
        mock_detection = MagicMock()
        mock_detection.class_name = "person"
        mock_detection.confidence = 0.6  # Below threshold
        
        mock_all = MagicMock()
        mock_all.detections = [mock_detection]
        
        mock_detector = AsyncMock()
        mock_detector.capture_all_from_camera.return_value = mock_all
        
        mock_logger = MagicMock()
        mock_resources = {"_deps": {}}
        
        with patch('src.rules.getParam', return_value=mock_logger):
            with patch('src.rules._get_vision_service', return_value=mock_detector):
                # We don't need to mock viam_to_pil_image here as it should never be called
                result = await eval_rule(rule, mock_resources)
                
                self.assertFalse(result["triggered"])
    
    async def test_tracker_rule_evaluation_unauthorized_person(self):
        """Test evaluating a tracker rule with an unauthorized person"""
        rule = RuleTracker()
        rule.type = "tracker"
        rule.tracker = "test_tracker"
        rule.camera = "test_camera"
        
        # Mock detection
        mock_detection = MagicMock()
        mock_detection.class_name = "person_123"
        mock_detection.x_min = 10
        mock_detection.y_min = 10
        mock_detection.x_max = 50
        mock_detection.y_max = 50
        
        # Mock all
        mock_all = MagicMock()
        mock_all.detections = [mock_detection]
        
        # Mock tracker's list_current response
        mock_current = {
            "list_current": {
                "person_123": {
                    "face_id_label": False,
                    "manual_label": False,
                    "re_id_label": False
                }
            }
        }
        
        # Mock tracker
        mock_tracker = AsyncMock()
        mock_tracker.capture_all_from_camera.return_value = mock_all
        mock_tracker.do_command.return_value = mock_current
        
        # Mock resources and logger
        mock_logger = MagicMock()
        mock_resources = {"_deps": {}}
        
        # Mock image processing
        mock_image = MagicMock()
        mock_cropped_image = MagicMock()
        mock_image.crop.return_value = mock_cropped_image
        
        with patch('src.rules.getParam', return_value=mock_logger):
            with patch('src.rules._get_vision_service', return_value=mock_tracker):
                with patch('src.rules.viam_to_pil_image', return_value=mock_image):
                    with patch('src.rules.re.sub', return_value="person_123"):
                        with patch('src.rules.logic.NOR', return_value=True):
                            result = await eval_rule(rule, mock_resources)
                            
                            self.assertTrue(result["triggered"])
                            self.assertEqual(result["resource"], "test_camera")
                            self.assertEqual(result["value"], "person_123")
                            mock_image.crop.assert_called_once_with((10, 10, 50, 50))
    
    async def test_tracker_rule_evaluation_authorized_person(self):
        """Test evaluating a tracker rule with an authorized person"""
        rule = RuleTracker()
        rule.type = "tracker"
        rule.tracker = "test_tracker"
        rule.camera = "test_camera"
        
        # Mock detection
        mock_detection = MagicMock()
        mock_detection.class_name = "person_123"
        
        # Mock all
        mock_all = MagicMock()
        mock_all.detections = [mock_detection]
        
        # Mock tracker's list_current response with authorized person
        mock_current = {
            "list_current": {
                "person_123": {
                    "face_id_label": True,  # Authorized
                    "manual_label": False,
                    "re_id_label": False
                }
            }
        }
        
        # Mock tracker
        mock_tracker = AsyncMock()
        mock_tracker.capture_all_from_camera.return_value = mock_all
        mock_tracker.do_command.return_value = mock_current
        
        # Mock resources and logger
        mock_logger = MagicMock()
        mock_resources = {"_deps": {}}
        
        with patch('src.rules.getParam', return_value=mock_logger):
            with patch('src.rules._get_vision_service', return_value=mock_tracker):
                with patch('src.rules.re.sub', return_value="person_123"):
                    with patch('src.rules.logic.NOR', return_value=False):  # Important: NOR is false when any input is true
                        result = await eval_rule(rule, mock_resources)
                        
                        self.assertFalse(result["triggered"])
                        self.assertTrue(result.get("known_person_seen", False))
    
    async def test_tracker_rule_evaluation_mixed_detections(self):
        """Test evaluating a tracker rule with both authorized and unauthorized persons"""
        rule = RuleTracker()
        rule.type = "tracker"
        rule.tracker = "test_tracker"
        rule.camera = "test_camera"
        
        # Mock detections - one authorized, one unauthorized
        mock_detection1 = MagicMock()
        mock_detection1.class_name = "authorized_person"
        
        mock_detection2 = MagicMock()
        mock_detection2.class_name = "unauthorized_person"
        mock_detection2.x_min = 10
        mock_detection2.y_min = 10
        mock_detection2.x_max = 50
        mock_detection2.y_max = 50
        
        # Mock all with both detections
        mock_all = MagicMock()
        mock_all.detections = [mock_detection1, mock_detection2]
        
        # Mock tracker's list_current response with both persons
        mock_current = {
            "list_current": {
                "authorized_person": {
                    "face_id_label": True,  # Authorized
                    "manual_label": False,
                    "re_id_label": False
                },
                "unauthorized_person": {
                    "face_id_label": False,  # Unauthorized
                    "manual_label": False,
                    "re_id_label": False
                }
            }
        }
        
        # Mock tracker
        mock_tracker = AsyncMock()
        mock_tracker.capture_all_from_camera.return_value = mock_all
        mock_tracker.do_command.return_value = mock_current
        
        # Mock resources and logger
        mock_logger = MagicMock()
        mock_resources = {"_deps": {}}
        
        # Define a side effect function for re.sub to handle different class names
        def mock_sub_side_effect(pattern, replacement, class_name):
            if "authorized_person" in class_name:
                return "authorized_person"
            else:
                return "unauthorized_person"
        
        # Mock authorized status side effect
        # The approved_status list would be [True, False] - one true means NOR is False
        
        with patch('src.rules.getParam', return_value=mock_logger):
            with patch('src.rules._get_vision_service', return_value=mock_tracker):
                with patch('src.rules.re.sub', side_effect=mock_sub_side_effect):
                    # Since at least one person is authorized, NOR will be false
                    with patch('src.rules.logic.NOR', return_value=False):
                        result = await eval_rule(rule, mock_resources)
                        
                        # Rule should not trigger because at least one person is authorized
                        self.assertFalse(result["triggered"])
                        # But we should know a known person was seen
                        self.assertTrue(result.get("known_person_seen", False))
    
    async def test_call_rule_evaluation_matching(self):
        """Test evaluating a call rule that matches criteria"""
        rule = RuleCall()
        rule.type = "call"
        rule.resource = "test_resource"
        rule.method = "test_method"
        rule.payload = '{"param": "value"}'
        rule.result_path = "temperature"
        rule.result_operator = "gt"
        rule.result_value = 25
        
        # Mock dependencies
        mock_call_result = {"temperature": 30}
        mock_logger = MagicMock()
        mock_resources = {}
        
        with patch('src.rules.getParam', return_value=mock_logger):
            with patch('src.rules.call_method', return_value=mock_call_result):
                result = await eval_rule(rule, mock_resources)
                
                self.assertTrue(result["triggered"])
                self.assertEqual(result["value"], 30)
                self.assertEqual(result["resource"], "test_resource")
    
    async def test_call_rule_evaluation_not_matching(self):
        """Test evaluating a call rule that doesn't match criteria"""
        rule = RuleCall()
        rule.type = "call"
        rule.resource = "test_resource"
        rule.method = "test_method"
        rule.payload = '{"param": "value"}'
        rule.result_path = "temperature"
        rule.result_operator = "gt"
        rule.result_value = 25
        
        # Mock dependencies
        mock_call_result = {"temperature": 20}  # Below threshold
        mock_logger = MagicMock()
        mock_resources = {}
        
        with patch('src.rules.getParam', return_value=mock_logger):
            with patch('src.rules.call_method', return_value=mock_call_result):
                result = await eval_rule(rule, mock_resources)
                
                self.assertFalse(result["triggered"])
                self.assertEqual(result["value"], 20)
                self.assertEqual(result["resource"], "test_resource")
    
    async def test_call_rule_with_result_function(self):
        """Test evaluating a call rule with result function"""
        rule = RuleCall()
        rule.type = "call"
        rule.resource = "test_resource"
        rule.method = "test_method"
        rule.result_path = "items"
        rule.result_function = "len"
        rule.result_operator = "eq"
        rule.result_value = 3
        
        # Mock dependencies
        mock_call_result = {"items": ["a", "b", "c"]}
        mock_logger = MagicMock()
        mock_resources = {}
        
        with patch('src.rules.getParam', return_value=mock_logger):
            with patch('src.rules.call_method', return_value=mock_call_result):
                result = await eval_rule(rule, mock_resources)
                
                self.assertTrue(result["triggered"])
                self.assertEqual(result["value"], 3)
    
    @patch('src.rules.call_method')
    @patch('src.rules.getParam')
    async def test_call_rule_with_multiple_operators(self, mock_get_param, mock_call_method):
        """Test evaluating a call rule with different result operators"""
        # Setup common mocks
        mock_logger = MagicMock()
        mock_get_param.return_value = mock_logger
        
        # Test each operator individually
        # Test equals operator
        rule = RuleCall()
        rule.type = "call"
        rule.resource = "test_resource"
        rule.method = "test_method"
        rule.result_path = "value"
        rule.result_operator = "eq"
        rule.result_value = 25
        
        mock_call_method.return_value = {"value": 25}
        result = await eval_rule(rule, {})
        self.assertTrue(result["triggered"], "equals operator failed")
        
        # Test not equals operator
        rule.result_operator = "ne"
        rule.result_value = 20
        
        mock_call_method.return_value = {"value": 25}
        result = await eval_rule(rule, {})
        self.assertTrue(result["triggered"], "not equals operator failed")
        
        # Test less than operator
        rule.result_operator = "lt"
        rule.result_value = 25
        
        mock_call_method.return_value = {"value": 20}
        result = await eval_rule(rule, {})
        self.assertTrue(result["triggered"], "less than operator failed")
        
        # Test less than or equal operator
        rule.result_operator = "lte"
        rule.result_value = 25
        
        mock_call_method.return_value = {"value": 25}
        result = await eval_rule(rule, {})
        self.assertTrue(result["triggered"], "less than or equal operator failed")
        
        # Test greater than operator
        rule.result_operator = "gt"
        rule.result_value = 25
        
        mock_call_method.return_value = {"value": 30}
        result = await eval_rule(rule, {})
        self.assertTrue(result["triggered"], "greater than operator failed")
        
        # Test greater than or equal operator
        rule.result_operator = "gte"
        rule.result_value = 25
        
        mock_call_method.return_value = {"value": 25}
        result = await eval_rule(rule, {})
        self.assertTrue(result["triggered"], "greater than or equal operator failed")
        
        # Test regex operator
        rule.result_operator = "regex"
        rule.result_value = r"abc\d+"
        
        mock_call_method.return_value = {"value": "abc123"}
        
        with patch('src.rules.re.match', return_value=True):
            result = await eval_rule(rule, {})
            self.assertTrue(result["triggered"], "regex operator failed")
        
        # Test in operator
        rule.result_operator = "in"
        rule.result_value = "b"
        
        mock_call_method.return_value = {"value": "abc"}
        result = await eval_rule(rule, {})
        self.assertTrue(result["triggered"], "in operator failed")
        
        # Test hasattr operator
        rule.result_operator = "hasattr"
        rule.result_value = "append"
        
        mock_call_method.return_value = {"value": []}
        result = await eval_rule(rule, {})
        self.assertTrue(result["triggered"], "hasattr operator failed")

if __name__ == '__main__':
    unittest.main() 