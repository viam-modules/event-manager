import unittest
import sys
import os
from pathlib import Path
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

# Add the source directory to the path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent))

from src.rules import RuleDetector, RuleClassifier, eval_rule

class TestDefaultClassRegex(unittest.IsolatedAsyncioTestCase):
    async def test_detector_default_class_regex(self):
        """Test that detector rule with default class_regex matches any class"""
        # Create rule with default class_regex
        rule = RuleDetector()
        rule.type = "detection"
        rule.camera = "cam1"
        rule.detector = "object_detector"
        rule.confidence_pct = 0.7
        # Not setting class_regex, so it uses default ".*"

        # Mock dependencies
        mock_detection = MagicMock()
        mock_detection.class_name = "random_object"  # Should match with default ".*"
        mock_detection.confidence = 0.8  # Above threshold
        
        mock_image = MagicMock()
        
        mock_camera = AsyncMock()
        mock_camera.get_image.return_value = mock_image
        
        mock_detector = AsyncMock()
        mock_detector.get_detections.return_value = [mock_detection]
        
        mock_logger = MagicMock()
        mock_resources = {"_deps": {}}
        
        # Create a mock PIL image
        mock_pil_image = MagicMock()
        
        with patch('src.rules.getParam', return_value=mock_logger):
            with patch('src.rules._get_vision_service', return_value=mock_detector):
                with patch('src.rules._get_camera_component', return_value=mock_camera):
                    with patch('src.rules.viam_to_pil_image', return_value=mock_pil_image):
                        result = await eval_rule(rule, mock_resources)
                        
                        self.assertTrue(result["triggered"])
                        self.assertEqual(result["value"], "random_object")
                        self.assertEqual(result["resource"], "cam1")
    
    async def test_detector_empty_class_regex(self):
        """Test that detector rule with empty class_regex matches any class"""
        # Create rule with empty class_regex
        rule = RuleDetector()
        rule.type = "detection"
        rule.camera = "cam1"
        rule.detector = "object_detector"
        rule.class_regex = ""  # Empty string should be converted to ".*"
        rule.confidence_pct = 0.7

        # Mock dependencies
        mock_detection = MagicMock()
        mock_detection.class_name = "random_object"  # Should match with ".*"
        mock_detection.confidence = 0.8  # Above threshold
        
        mock_image = MagicMock()
        
        mock_camera = AsyncMock()
        mock_camera.get_image.return_value = mock_image
        
        mock_detector = AsyncMock()
        mock_detector.get_detections.return_value = [mock_detection]
        
        mock_logger = MagicMock()
        mock_resources = {"_deps": {}}
        
        # Create a mock PIL image
        mock_pil_image = MagicMock()
        
        with patch('src.rules.getParam', return_value=mock_logger):
            with patch('src.rules._get_vision_service', return_value=mock_detector):
                with patch('src.rules._get_camera_component', return_value=mock_camera):
                    with patch('src.rules.viam_to_pil_image', return_value=mock_pil_image):
                        result = await eval_rule(rule, mock_resources)
                        
                        self.assertTrue(result["triggered"])
                        self.assertEqual(result["value"], "random_object")
                        self.assertEqual(result["resource"], "cam1")
    
    async def test_classifier_default_class_regex(self):
        """Test that classifier rule with default class_regex matches any class"""
        # Create rule with default class_regex
        rule = RuleClassifier()
        rule.type = "classification"
        rule.camera = "cam1"
        rule.classifier = "image_classifier"
        rule.confidence_pct = 0.7
        # Not setting class_regex, so it uses default ".*"

        # Mock dependencies
        mock_classification = MagicMock()
        mock_classification.class_name = "random_class"  # Should match with default ".*"
        mock_classification.confidence = 0.8  # Above threshold
        
        mock_image = MagicMock()
        
        mock_camera = AsyncMock()
        mock_camera.get_image.return_value = mock_image
        
        mock_classifier = AsyncMock()
        mock_classifier.get_classifications.return_value = [mock_classification]
        
        mock_logger = MagicMock()
        mock_resources = {"_deps": {}}
        
        # Create a mock PIL image
        mock_pil_image = MagicMock()
        
        with patch('src.rules.getParam', return_value=mock_logger):
            with patch('src.rules._get_vision_service', return_value=mock_classifier):
                with patch('src.rules._get_camera_component', return_value=mock_camera):
                    with patch('src.rules.viam_to_pil_image', return_value=mock_pil_image):
                        result = await eval_rule(rule, mock_resources)
                        
                        self.assertTrue(result["triggered"])
                        self.assertEqual(result["value"], "random_class")
                        self.assertEqual(result["resource"], "cam1")
    
    async def test_classifier_empty_class_regex(self):
        """Test that classifier rule with empty class_regex matches any class"""
        # Create rule with empty class_regex
        rule = RuleClassifier()
        rule.type = "classification"
        rule.camera = "cam1"
        rule.classifier = "image_classifier"
        rule.class_regex = ""  # Empty string should be converted to ".*"
        rule.confidence_pct = 0.7

        # Mock dependencies
        mock_classification = MagicMock()
        mock_classification.class_name = "random_class"  # Should match with ".*"
        mock_classification.confidence = 0.8  # Above threshold
        
        mock_image = MagicMock()
        
        mock_camera = AsyncMock()
        mock_camera.get_image.return_value = mock_image
        
        mock_classifier = AsyncMock()
        mock_classifier.get_classifications.return_value = [mock_classification]
        
        mock_logger = MagicMock()
        mock_resources = {"_deps": {}}
        
        # Create a mock PIL image
        mock_pil_image = MagicMock()
        
        with patch('src.rules.getParam', return_value=mock_logger):
            with patch('src.rules._get_vision_service', return_value=mock_classifier):
                with patch('src.rules._get_camera_component', return_value=mock_camera):
                    with patch('src.rules.viam_to_pil_image', return_value=mock_pil_image):
                        result = await eval_rule(rule, mock_resources)
                        
                        self.assertTrue(result["triggered"])
                        self.assertEqual(result["value"], "random_class")
                        self.assertEqual(result["resource"], "cam1")

if __name__ == '__main__':
    unittest.main() 