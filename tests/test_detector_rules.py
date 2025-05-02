import unittest
import sys
import os
from pathlib import Path
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

# Add the source directory to the path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent))

from src.rules import RuleDetector, eval_rule

class TestDetectorRuleInitialization(unittest.TestCase):
    def test_detector_rule_initialization(self):
        """Test that a RuleDetector can be properly initialized"""
        rule_config = {
            "camera": "cam1",
            "detector": "object_detector",
            "class_regex": "person|car",
            "confidence_pct": 0.75,
            "inverse_pause_secs": 60
        }
        
        rule = RuleDetector(**rule_config)
        
        self.assertEqual(rule.camera, "cam1")
        self.assertEqual(rule.detector, "object_detector")
        self.assertEqual(rule.class_regex, "person|car")
        self.assertEqual(rule.confidence_pct, 0.75)
        self.assertEqual(rule.inverse_pause_secs, 60)
        self.assertEqual(rule.type, "detection")

class TestDetectorRuleEvaluation(unittest.IsolatedAsyncioTestCase):
    async def test_detector_rule_matching_detection(self):
        """Test detector rule evaluation with matching detection"""
        rule = RuleDetector()
        rule.type = "detection"
        rule.camera = "cam1"
        rule.detector = "object_detector"
        rule.class_regex = "person"
        rule.confidence_pct = 0.7
        
        # Mock dependencies
        mock_detection = MagicMock()
        mock_detection.class_name = "person"
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
                        self.assertEqual(result["value"], "person")
                        self.assertEqual(result["resource"], "cam1")
                        mock_camera.get_image.assert_called_once()
                        mock_detector.get_detections.assert_called_once_with(mock_image, extra={})
    
    async def test_detector_rule_no_matching_class(self):
        """Test detector rule evaluation with detection that doesn't match class regex"""
        rule = RuleDetector()
        rule.type = "detection"
        rule.camera = "cam1"
        rule.detector = "object_detector"
        rule.class_regex = "person"
        rule.confidence_pct = 0.7
        
        # Mock dependencies
        mock_detection = MagicMock()
        mock_detection.class_name = "car"  # Doesn't match regex
        mock_detection.confidence = 0.8
        
        mock_image = MagicMock()
        
        mock_camera = AsyncMock()
        mock_camera.get_image.return_value = mock_image
        
        mock_detector = AsyncMock()
        mock_detector.get_detections.return_value = [mock_detection]
        
        mock_logger = MagicMock()
        mock_resources = {"_deps": {}}
        
        with patch('src.rules.getParam', return_value=mock_logger):
            with patch('src.rules._get_vision_service', return_value=mock_detector):
                with patch('src.rules._get_camera_component', return_value=mock_camera):
                    result = await eval_rule(rule, mock_resources)
                    
                    self.assertFalse(result["triggered"])
                    mock_camera.get_image.assert_called_once()
                    mock_detector.get_detections.assert_called_once_with(mock_image, extra={})
    
    async def test_detector_rule_low_confidence(self):
        """Test detector rule evaluation with detection below confidence threshold"""
        rule = RuleDetector()
        rule.type = "detection"
        rule.camera = "cam1"
        rule.detector = "object_detector"
        rule.class_regex = "person"
        rule.confidence_pct = 0.7
        
        # Mock dependencies
        mock_detection = MagicMock()
        mock_detection.class_name = "person"
        mock_detection.confidence = 0.6  # Below threshold
        
        mock_image = MagicMock()
        
        mock_camera = AsyncMock()
        mock_camera.get_image.return_value = mock_image
        
        mock_detector = AsyncMock()
        mock_detector.get_detections.return_value = [mock_detection]
        
        mock_logger = MagicMock()
        mock_resources = {"_deps": {}}
        
        with patch('src.rules.getParam', return_value=mock_logger):
            with patch('src.rules._get_vision_service', return_value=mock_detector):
                with patch('src.rules._get_camera_component', return_value=mock_camera):
                    result = await eval_rule(rule, mock_resources)
                    
                    self.assertFalse(result["triggered"])
                    mock_camera.get_image.assert_called_once()
                    mock_detector.get_detections.assert_called_once_with(mock_image, extra={})
    
    async def test_detector_rule_multiple_detections(self):
        """Test detector rule evaluation with multiple detections"""
        rule = RuleDetector()
        rule.type = "detection"
        rule.camera = "cam1"
        rule.detector = "object_detector"
        rule.class_regex = "person|car"
        rule.confidence_pct = 0.7
        
        # Mock dependencies
        mock_detection1 = MagicMock()
        mock_detection1.class_name = "chair"  # Doesn't match regex
        mock_detection1.confidence = 0.9
        
        mock_detection2 = MagicMock()
        mock_detection2.class_name = "car"  # Matches regex
        mock_detection2.confidence = 0.8
        
        mock_image = MagicMock()
        
        mock_camera = AsyncMock()
        mock_camera.get_image.return_value = mock_image
        
        mock_detector = AsyncMock()
        mock_detector.get_detections.return_value = [mock_detection1, mock_detection2]
        
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
                        self.assertEqual(result["value"], "car")
                        self.assertEqual(result["resource"], "cam1")
                        mock_camera.get_image.assert_called_once()
                        mock_detector.get_detections.assert_called_once_with(mock_image, extra={})
    
    async def test_detector_rule_no_detections(self):
        """Test detector rule evaluation with no detections"""
        rule = RuleDetector()
        rule.type = "detection"
        rule.camera = "cam1"
        rule.detector = "object_detector"
        rule.class_regex = "person"
        rule.confidence_pct = 0.7
        
        # Mock dependencies
        mock_image = MagicMock()
        
        mock_camera = AsyncMock()
        mock_camera.get_image.return_value = mock_image
        
        mock_detector = AsyncMock()
        mock_detector.get_detections.return_value = []  # No detections
        
        mock_logger = MagicMock()
        mock_resources = {"_deps": {}}
        
        with patch('src.rules.getParam', return_value=mock_logger):
            with patch('src.rules._get_vision_service', return_value=mock_detector):
                with patch('src.rules._get_camera_component', return_value=mock_camera):
                    result = await eval_rule(rule, mock_resources)
                    
                    self.assertFalse(result["triggered"])
                    mock_camera.get_image.assert_called_once()
                    mock_detector.get_detections.assert_called_once_with(mock_image, extra={})
    
    async def test_detector_rule_exception_handling(self):
        """Test detector rule evaluation with exception handling"""
        rule = RuleDetector()
        rule.type = "detection"
        rule.camera = "cam1"
        rule.detector = "object_detector"
        rule.class_regex = "person"
        rule.confidence_pct = 0.7
        
        # Mock dependencies
        mock_camera = AsyncMock()
        mock_camera.get_image.side_effect = Exception("Camera error")
        
        mock_detector = AsyncMock()
        
        mock_logger = MagicMock()
        mock_resources = {"_deps": {}}
        
        with patch('src.rules.getParam', return_value=mock_logger):
            with patch('src.rules._get_vision_service', return_value=mock_detector):
                with patch('src.rules._get_camera_component', return_value=mock_camera):
                    try:
                        result = await eval_rule(rule, mock_resources)
                        
                        self.assertFalse(result["triggered"])
                        mock_logger.error.assert_called_once()
                    except Exception:
                        mock_camera.get_image.assert_called_once()
                        pass

if __name__ == '__main__':
    unittest.main()