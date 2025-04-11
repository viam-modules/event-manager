import unittest
import sys
import os
from pathlib import Path

# Add the source directory to the path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent))

from src.logic import AND, OR, XOR, NAND, NOR, XNOR

class TestLogicFunctions(unittest.TestCase):
    def test_and_function(self):
        """Test the AND logic function"""
        self.assertTrue(AND([True, True, True]))
        self.assertFalse(AND([True, False, True]))
        self.assertFalse(AND([False, False, False]))
        self.assertFalse(AND([]))  # Empty list
    
    def test_or_function(self):
        """Test the OR logic function"""
        self.assertTrue(OR([True, False, False]))
        self.assertTrue(OR([True, True, True]))
        self.assertFalse(OR([False, False, False]))
        self.assertFalse(OR([]))  # Empty list
    
    def test_xor_function(self):
        """Test the XOR logic function"""
        self.assertFalse(XOR([True, True]))
        self.assertTrue(XOR([True, False]))
        self.assertTrue(XOR([False, True]))
        self.assertFalse(XOR([False, False]))
        self.assertFalse(XOR([True, True, True]))
        self.assertTrue(XOR([True, False, False]))
        self.assertFalse(XOR([]))  # Empty list
    
    def test_nand_function(self):
        """Test the NAND logic function"""
        self.assertFalse(NAND([True, True, True]))
        self.assertTrue(NAND([True, False, True]))
        self.assertTrue(NAND([False, False, False]))
        self.assertTrue(NAND([]))  # Empty list
    
    def test_nor_function(self):
        """Test the NOR logic function"""
        self.assertFalse(NOR([True, False, False]))
        self.assertFalse(NOR([True, True, True]))
        self.assertTrue(NOR([False, False, False]))
        self.assertTrue(NOR([]))  # Empty list
    
    def test_xnor_function(self):
        """Test the XNOR logic function"""
        self.assertTrue(XNOR([True, True]))
        self.assertFalse(XNOR([True, False]))
        self.assertFalse(XNOR([False, True]))
        self.assertTrue(XNOR([False, False]))
        self.assertTrue(XNOR([True, True, True]))
        self.assertFalse(XNOR([True, False, False]))
        self.assertTrue(XNOR([]))  # Empty list

if __name__ == '__main__':
    unittest.main() 