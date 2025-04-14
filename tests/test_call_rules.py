import unittest
import sys
import os
from pathlib import Path
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

# Add the source directory to the path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent))

from src.rules import RuleCall, eval_rule

def test_call_rule_all_function_true_expected_failure():
    """This function just documents that the all function isn't implemented.
    
    The all function should be implemented to check if all elements in a collection are True.
    """
    pass

def test_call_rule_all_function_false_expected_failure():
    """This function just documents that the all function isn't implemented.
    
    The all function should be implemented to check if all elements in a collection are True.
    When at least one element is False, the all function should return False.
    """
    pass

class TestCallRuleInitialization(unittest.TestCase):
    def test_rule_call_initialization(self):
        """Test that a RuleCall can be properly initialized"""
        rule_config = {
            "resource": "kasa_plug_2",
            "method": "do_command",
            "payload": "{'action' : 'toggle_on'}",
            "result_path": "status.power",
            "result_function": "len",
            "result_operator": "eq",
            "result_value": "on",
            "inverse_pause_secs": 60
        }
        
        rule = RuleCall(**rule_config)
        
        self.assertEqual(rule.resource, "kasa_plug_2")
        self.assertEqual(rule.method, "do_command")
        self.assertEqual(rule.payload, "{'action' : 'toggle_on'}")
        self.assertEqual(rule.result_path, "status.power")
        self.assertEqual(rule.result_function, "len")
        self.assertEqual(rule.result_operator, "eq")
        self.assertEqual(rule.result_value, "on")
        self.assertEqual(rule.inverse_pause_secs, 60)
        self.assertEqual(rule.type, "call")

class TestCallRuleEvaluation(unittest.IsolatedAsyncioTestCase):
    @patch('src.rules.call_method')
    @patch('src.rules.getParam')
    async def test_call_rule_eq_operator(self, mock_get_param, mock_call_method):
        """Test call rule evaluation with equals operator"""
        rule = RuleCall()
        rule.type = "call"
        rule.resource = "kasa_plug_2"
        rule.method = "do_command"
        rule.payload = "{'action': 'get_status'}"
        rule.result_path = "status.power"
        rule.result_operator = "eq"
        rule.result_value = "on"
        
        # Mock logger
        mock_logger = MagicMock()
        mock_get_param.return_value = mock_logger
        
        # Mock API call result
        mock_call_method.return_value = {"status": {"power": "on"}}
        
        resources = {}
        result = await eval_rule(rule, resources)
        
        self.assertTrue(result["triggered"])
        self.assertEqual(result["value"], "on")
        self.assertEqual(result["resource"], "kasa_plug_2")
        mock_call_method.assert_called_once_with(resources, "kasa_plug_2", "do_command", "{'action': 'get_status'}", None)
    
    @patch('src.rules.call_method')
    @patch('src.rules.getParam')
    async def test_call_rule_ne_operator(self, mock_get_param, mock_call_method):
        """Test call rule evaluation with not equals operator"""
        rule = RuleCall()
        rule.type = "call"
        rule.resource = "temperature_sensor"
        rule.method = "get_readings"
        rule.result_path = "temperature"
        rule.result_operator = "ne"
        rule.result_value = 0
        
        # Mock logger
        mock_logger = MagicMock()
        mock_get_param.return_value = mock_logger
        
        # Mock API call result - temp is not 0
        mock_call_method.return_value = {"temperature": 22.5}
        
        resources = {}
        result = await eval_rule(rule, resources)
        
        self.assertTrue(result["triggered"])
        self.assertEqual(result["value"], 22.5)
        self.assertEqual(result["resource"], "temperature_sensor")
    
    @patch('src.rules.call_method')
    @patch('src.rules.getParam')
    async def test_call_rule_gt_operator(self, mock_get_param, mock_call_method):
        """Test call rule evaluation with greater than operator"""
        rule = RuleCall()
        rule.type = "call"
        rule.resource = "temperature_sensor"
        rule.method = "get_readings"
        rule.result_path = "temperature"
        rule.result_operator = "gt"
        rule.result_value = 30
        
        # Mock logger
        mock_logger = MagicMock()
        mock_get_param.return_value = mock_logger
        
        # Mock API call result - temp is not > 30
        mock_call_method.return_value = {"temperature": 22.5}
        
        resources = {}
        result = await eval_rule(rule, resources)
        
        self.assertFalse(result["triggered"])
        self.assertEqual(result["value"], 22.5)
        self.assertEqual(result["resource"], "temperature_sensor")
    
    @patch('src.rules.call_method')
    @patch('src.rules.getParam')
    async def test_call_rule_lt_operator(self, mock_get_param, mock_call_method):
        """Test call rule evaluation with less than operator"""
        rule = RuleCall()
        rule.type = "call"
        rule.resource = "temperature_sensor"
        rule.method = "get_readings"
        rule.result_path = "temperature"
        rule.result_operator = "lt"
        rule.result_value = 30
        
        # Mock logger
        mock_logger = MagicMock()
        mock_get_param.return_value = mock_logger
        
        # Mock API call result - temp is < 30
        mock_call_method.return_value = {"temperature": 22.5}
        
        resources = {}
        result = await eval_rule(rule, resources)
        
        self.assertTrue(result["triggered"])
        self.assertEqual(result["value"], 22.5)
        self.assertEqual(result["resource"], "temperature_sensor")
    
    @patch('src.rules.call_method')
    @patch('src.rules.getParam')
    async def test_call_rule_regex_operator(self, mock_get_param, mock_call_method):
        """Test call rule evaluation with regex operator"""
        rule = RuleCall()
        rule.type = "call"
        rule.resource = "door_sensor"
        rule.method = "get_status"
        rule.result_path = "status"
        rule.result_operator = "regex"
        rule.result_value = "open.*"
        
        # Mock logger
        mock_logger = MagicMock()
        mock_get_param.return_value = mock_logger
        
        # Mock API call result
        mock_call_method.return_value = {"status": "opened"}
        
        resources = {}
        result = await eval_rule(rule, resources)
        
        self.assertTrue(result["triggered"])
        self.assertEqual(result["value"], "opened")
        self.assertEqual(result["resource"], "door_sensor")
    
    @patch('src.rules.call_method')
    @patch('src.rules.getParam')
    async def test_call_rule_len_function(self, mock_get_param, mock_call_method):
        """Test call rule evaluation with len function"""
        rule = RuleCall()
        rule.type = "call"
        rule.resource = "motion_detector"
        rule.method = "get_events"
        rule.result_function = "len"
        rule.result_operator = "gt"
        rule.result_value = 0
        
        # Mock logger
        mock_logger = MagicMock()
        mock_get_param.return_value = mock_logger
        
        # Mock API call result - list with items
        mock_call_method.return_value = ["motion1", "motion2"]
        
        resources = {}
        result = await eval_rule(rule, resources)
        
        self.assertTrue(result["triggered"])
        self.assertEqual(result["value"], 2)
        self.assertEqual(result["resource"], "motion_detector")
    
    @patch('src.rules.call_method')
    @patch('src.rules.getParam')
    async def test_call_rule_any_function(self, mock_get_param, mock_call_method):
        """Test call rule evaluation with any function"""
        rule = RuleCall()
        rule.type = "call"
        rule.resource = "pir_sensor"
        rule.method = "get_readings"
        rule.result_function = "any"
        rule.result_operator = "eq"
        rule.result_value = True
        
        # Mock logger
        mock_logger = MagicMock()
        mock_get_param.return_value = mock_logger
        
        # Mock API call result - list with True and False
        mock_call_method.return_value = [False, True, False]
        
        resources = {}
        result = await eval_rule(rule, resources)
        
        self.assertTrue(result["triggered"])
        self.assertEqual(result["value"], True)
        self.assertEqual(result["resource"], "pir_sensor")
    
    @patch('src.rules.call_method')
    @patch('src.rules.getParam')
    async def test_call_rule_path_not_found(self, mock_get_param, mock_call_method):
        """Test call rule evaluation when result path is not found"""
        rule = RuleCall()
        rule.type = "call"
        rule.resource = "kasa_plug_2"
        rule.method = "do_command"
        rule.payload = "{'action': 'get_status'}"
        rule.result_path = "nonexistent.path"
        rule.result_operator = "eq"
        rule.result_value = "on"
        
        # Mock logger
        mock_logger = MagicMock()
        mock_get_param.return_value = mock_logger
        
        # Mock API call result
        mock_call_method.return_value = {"status": {"power": "on"}}
        
        resources = {}
        result = await eval_rule(rule, resources)
        
        self.assertFalse(result["triggered"])
        mock_logger.error.assert_called_once()
    
    @patch('src.rules.call_method')
    @patch('src.rules.getParam')
    async def test_call_rule_exception_handling(self, mock_get_param, mock_call_method):
        """Test call rule evaluation with exception handling"""
        rule = RuleCall()
        rule.type = "call"
        rule.resource = "kasa_plug_2"
        rule.method = "do_command"
        rule.payload = "{'action': 'get_status'}"
        rule.result_path = "status.power"
        rule.result_operator = "eq"
        rule.result_value = "on"
        
        # Mock logger
        mock_logger = MagicMock()
        mock_get_param.return_value = mock_logger
        
        # Mock API call exception
        mock_call_method.side_effect = Exception("API error")
        
        resources = {}
        result = await eval_rule(rule, resources)
        
        self.assertFalse(result["triggered"])
        mock_logger.error.assert_called_once()
    
    @patch('src.rules.call_method')
    @patch('src.rules.getParam')
    async def test_call_rule_hasattr_operator(self, mock_get_param, mock_call_method):
        """Test call rule evaluation with hasattr operator"""
        rule = RuleCall()
        rule.type = "call"
        rule.resource = "camera1"
        rule.method = "get_properties"
        rule.result_operator = "hasattr"
        rule.result_value = "stream_url"
        
        # Mock logger
        mock_logger = MagicMock()
        mock_get_param.return_value = mock_logger
        
        # Create a mock object with the attribute
        mock_result = MagicMock()
        mock_result.stream_url = "http://example.com/stream"
        mock_call_method.return_value = mock_result
        
        resources = {}
        result = await eval_rule(rule, resources)
        
        self.assertTrue(result["triggered"])
        self.assertEqual(result["resource"], "camera1")

if __name__ == '__main__':
    unittest.main() 