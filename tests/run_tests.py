#!/usr/bin/env python3
import unittest
import sys
import os
from pathlib import Path

# Add the source directory to the path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent))

# Import test modules
from tests.test_events import TestEvent
from tests.test_rules import TestRules, TestRuleEvaluation
from tests.test_rules_evaluation import (
    TestRuleTrackerInitialization, 
    TestGetValueByDotNotation,
    TestLogicalTrigger,
    TestRuleEvaluation as TestRuleEvaluationExt
)
from tests.test_classifier_rules import (
    TestClassifierRuleEvaluation,
    TestErrorHandling
)
from tests.test_logic import TestLogicFunctions

def create_test_suite():
    """Create a test suite with all tests"""
    # Create a loader
    loader = unittest.TestLoader()
    
    # Create a test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases - Basic initialization tests
    test_suite.addTests(loader.loadTestsFromTestCase(TestEvent))
    test_suite.addTests(loader.loadTestsFromTestCase(TestRules))
    test_suite.addTests(loader.loadTestsFromTestCase(TestRuleEvaluation))
    # TestEventManagerBasics is a pytest class, not a unittest class
    # TestNotificationClasses is also a pytest class, not a unittest class
    
    # Add rule evaluation tests
    test_suite.addTests(loader.loadTestsFromTestCase(TestRuleTrackerInitialization))
    test_suite.addTests(loader.loadTestsFromTestCase(TestGetValueByDotNotation))
    test_suite.addTests(loader.loadTestsFromTestCase(TestLogicalTrigger))
    test_suite.addTests(loader.loadTestsFromTestCase(TestRuleEvaluationExt))
    
    # Add classifier and error handling tests
    test_suite.addTests(loader.loadTestsFromTestCase(TestClassifierRuleEvaluation))
    test_suite.addTests(loader.loadTestsFromTestCase(TestErrorHandling))
    
    # Add logic function tests
    test_suite.addTests(loader.loadTestsFromTestCase(TestLogicFunctions))
    
    # TestStatePersistence is a pytest class, not a unittest class
    
    return test_suite

if __name__ == '__main__':
    # Create test suite
    suite = create_test_suite()
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with appropriate code
    sys.exit(not result.wasSuccessful()) 