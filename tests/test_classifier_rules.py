import unittest
import sys
import os
from pathlib import Path
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

# Add the source directory to the path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent))

from src.rules import RuleClassifier, RuleCall, eval_rule

class TestClassifierRuleEvaluation(unittest.IsolatedAsyncioTestCase):
    async def test_classifier_rule_evaluation_matching(self):
        """Test evaluating a classifier rule with matching classifications"""
        rule = RuleClassifier()
        rule.type = "classification"
        rule.classifier = "test_classifier"
        rule.camera = "test_camera"
        rule.confidence_pct = 0.7
        rule.class_regex = "cat"
        
        # Mock dependencies
        mock_classification = MagicMock()
        mock_classification.class_name = "cat"
        mock_classification.confidence = 0.8
        
        mock_all = MagicMock()
        mock_all.classifications = [mock_classification]
        
        mock_classifier = AsyncMock()
        mock_classifier.capture_all_from_camera.return_value = mock_all
        
        mock_logger = MagicMock()
        mock_resources = {"_deps": {}}
        
        # Create a mock PIL image
        mock_pil_image = MagicMock()
        
        with patch('src.rules.getParam', return_value=mock_logger):
            with patch('src.rules._get_vision_service', return_value=mock_classifier):
                with patch('src.rules.viam_to_pil_image', return_value=mock_pil_image):
                    result = await eval_rule(rule, mock_resources)
                    
                    self.assertTrue(result["triggered"])
                    mock_classifier.capture_all_from_camera.assert_called_once_with(
                        "test_camera", return_classifications=True, return_image=True
                    )
                    self.assertEqual(result["value"], "cat")
                    self.assertEqual(result["resource"], "test_camera")
    
    async def test_classifier_rule_evaluation_wrong_class(self):
        """Test evaluating a classifier rule with non-matching class name"""
        rule = RuleClassifier()
        rule.type = "classification"
        rule.classifier = "test_classifier"
        rule.camera = "test_camera"
        rule.confidence_pct = 0.7
        rule.class_regex = "cat"
        
        # Mock dependencies with non-matching class name
        mock_classification = MagicMock()
        mock_classification.class_name = "dog"
        mock_classification.confidence = 0.8
        
        mock_all = MagicMock()
        mock_all.classifications = [mock_classification]
        
        mock_classifier = AsyncMock()
        mock_classifier.capture_all_from_camera.return_value = mock_all
        
        mock_logger = MagicMock()
        mock_resources = {"_deps": {}}
        
        with patch('src.rules.getParam', return_value=mock_logger):
            with patch('src.rules._get_vision_service', return_value=mock_classifier):
                # Don't need to mock viam_to_pil_image here as it shouldn't be called
                result = await eval_rule(rule, mock_resources)
                
                self.assertFalse(result["triggered"])
    
    async def test_classifier_rule_evaluation_low_confidence(self):
        """Test evaluating a classifier rule with low confidence score"""
        rule = RuleClassifier()
        rule.type = "classification"
        rule.classifier = "test_classifier"
        rule.camera = "test_camera"
        rule.confidence_pct = 0.7
        rule.class_regex = "cat"
        
        # Mock dependencies with low confidence
        mock_classification = MagicMock()
        mock_classification.class_name = "cat"
        mock_classification.confidence = 0.6  # Below threshold
        
        mock_all = MagicMock()
        mock_all.classifications = [mock_classification]
        
        mock_classifier = AsyncMock()
        mock_classifier.capture_all_from_camera.return_value = mock_all
        
        mock_logger = MagicMock()
        mock_resources = {"_deps": {}}
        
        with patch('src.rules.getParam', return_value=mock_logger):
            with patch('src.rules._get_vision_service', return_value=mock_classifier):
                # Don't need to mock viam_to_pil_image here as it shouldn't be called
                result = await eval_rule(rule, mock_resources)
                
                self.assertFalse(result["triggered"])
    
    async def test_classifier_rule_with_multiple_classifications(self):
        """Test evaluating a classifier rule with multiple classifications"""
        rule = RuleClassifier()
        rule.type = "classification"
        rule.classifier = "test_classifier"
        rule.camera = "test_camera"
        rule.confidence_pct = 0.7
        rule.class_regex = "(cat|dog)"  # Matches both cat and dog
        
        # Mock dependencies with multiple classifications
        mock_classifications = [
            MagicMock(class_name="bird", confidence=0.9),
            MagicMock(class_name="dog", confidence=0.8),
            MagicMock(class_name="cat", confidence=0.6)  # Below threshold
        ]
        
        mock_all = MagicMock()
        mock_all.classifications = mock_classifications
        
        mock_classifier = AsyncMock()
        mock_classifier.capture_all_from_camera.return_value = mock_all
        
        mock_logger = MagicMock()
        mock_resources = {"_deps": {}}
        
        # Create a mock PIL image
        mock_pil_image = MagicMock()
        
        with patch('src.rules.getParam', return_value=mock_logger):
            with patch('src.rules._get_vision_service', return_value=mock_classifier):
                with patch('src.rules.viam_to_pil_image', return_value=mock_pil_image):
                    result = await eval_rule(rule, mock_resources)
                    
                    self.assertTrue(result["triggered"])
                    self.assertEqual(result["value"], "dog")

class TestErrorHandling(unittest.IsolatedAsyncioTestCase):
    async def test_call_rule_with_error(self):
        """Test error handling in call rule evaluation"""
        rule = RuleCall()
        rule.type = "call"
        rule.resource = "test_resource"
        rule.method = "test_method"
        
        # Mock dependencies to raise an exception
        mock_logger = MagicMock()
        mock_resources = {}
        
        with patch('src.rules.getParam', return_value=mock_logger):
            with patch('src.rules.call_method', side_effect=Exception("Test error")):
                result = await eval_rule(rule, mock_resources)
                
                self.assertFalse(result["triggered"])
                mock_logger.error.assert_called()
    
    async def test_call_rule_with_missing_result_path(self):
        """Test call rule with missing result path"""
        rule = RuleCall()
        rule.type = "call"
        rule.resource = "test_resource"
        rule.method = "test_method"
        rule.result_path = "nonexistent.path"
        
        # Mock dependencies
        mock_call_result = {"temperature": 30}  # Does not contain nonexistent.path
        mock_logger = MagicMock()
        mock_resources = {}
        
        with patch('src.rules.getParam', return_value=mock_logger):
            with patch('src.rules.call_method', return_value=mock_call_result):
                result = await eval_rule(rule, mock_resources)
                
                self.assertFalse(result["triggered"])
                mock_logger.error.assert_called()
    
    async def test_unknown_rule_type(self):
        """Test evaluating a rule with unknown type"""
        rule = MagicMock()
        rule.type = "unknown_type"
        
        mock_logger = MagicMock()
        mock_resources = {}
        
        with patch('src.rules.getParam', return_value=mock_logger):
            result = await eval_rule(rule, mock_resources)
            
            self.assertFalse(result["triggered"])

if __name__ == '__main__':
    unittest.main() 