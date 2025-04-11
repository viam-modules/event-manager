import unittest
import sys
import os
from pathlib import Path
import asyncio

# Add the source directory to the path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent))

from src.rules import RuleDetector, RuleClassifier, RuleTime, RuleTracker, RuleCall, TimeRange

class TestRules(unittest.TestCase):
    def test_rule_detector_initialization(self):
        """Test that a RuleDetector can be properly initialized"""
        rule_config = {
            "camera": "camera1",
            "labels": ["person", "car"],
            "confidence": 0.75,
            "min_area": 0.1,
            "max_area": 0.8
        }
        
        rule = RuleDetector(**rule_config)
        
        self.assertEqual(rule.camera, "camera1")
        self.assertEqual(rule.labels, ["person", "car"])
        self.assertEqual(rule.confidence, 0.75)
        self.assertEqual(rule.min_area, 0.1)
        self.assertEqual(rule.max_area, 0.8)
    
    def test_rule_classifier_initialization(self):
        """Test that a RuleClassifier can be properly initialized"""
        rule_config = {
            "camera": "camera1",
            "classifier": "classifier1",
            "labels": ["cat", "dog"],
            "confidence": 0.8
        }
        
        rule = RuleClassifier(**rule_config)
        
        self.assertEqual(rule.camera, "camera1")
        self.assertEqual(rule.classifier, "classifier1")
        self.assertEqual(rule.labels, ["cat", "dog"])
        self.assertEqual(rule.confidence, 0.8)
    
    def test_rule_time_initialization(self):
        """Test that a RuleTime can be properly initialized"""
        rule_config = {
            "ranges": [
                {
                    "start_hour": 8,
                    "end_hour": 17
                },
                {
                    "start_hour": 20,
                    "end_hour": 22
                }
            ]
        }
        
        rule = RuleTime(**rule_config)
        
        self.assertEqual(len(rule.ranges), 2)
        self.assertEqual(rule.ranges[0].start_hour, 8)
        self.assertEqual(rule.ranges[0].end_hour, 17)
        self.assertEqual(rule.ranges[1].start_hour, 20)
        self.assertEqual(rule.ranges[1].end_hour, 22)

class TestRuleEvaluation(unittest.TestCase):
    """
    These tests would ideally mock the dependencies to test rule evaluation logic
    For now, we're just testing the initialization
    """
    pass

if __name__ == '__main__':
    unittest.main() 