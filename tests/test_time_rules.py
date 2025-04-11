import pytest
import sys
import os
from pathlib import Path
import asyncio
from unittest.mock import MagicMock, patch
from datetime import datetime

# Add the source directory to the path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent))

from src.rules import RuleTime, TimeRange, eval_rule

class TestTimeRuleInitialization:
    def test_time_range_initialization(self):
        """Test that a TimeRange can be properly initialized"""
        time_range_config = {
            "start_hour": 8,
            "end_hour": 17
        }
        
        time_range = TimeRange(**time_range_config)
        
        assert time_range.start_hour == 8
        assert time_range.end_hour == 17
    
    def test_time_rule_initialization(self):
        """Test that a RuleTime can be properly initialized with ranges"""
        rule_config = {
            "ranges": [
                {"start_hour": 8, "end_hour": 12},
                {"start_hour": 13, "end_hour": 17}
            ]
        }
        
        rule = RuleTime(**rule_config)
        
        assert rule.type == "time"
        assert len(rule.ranges) == 2
        assert rule.ranges[0].start_hour == 8
        assert rule.ranges[0].end_hour == 12
        assert rule.ranges[1].start_hour == 13
        assert rule.ranges[1].end_hour == 17

@pytest.mark.asyncio
class TestTimeRuleEvaluation:
    async def test_time_rule_within_range(self):
        """Test time rule evaluation when current time is within range"""
        rule = RuleTime()
        rule.ranges = [
            TimeRange(start_hour=9, end_hour=17)
        ]
        
        # Mock current time to be 12:00 (noon) which is within range
        with patch('src.rules.datetime') as mock_datetime:
            mock_now = MagicMock()
            mock_now.hour = 12
            mock_datetime.now.return_value = mock_now
            
            # Mock logger
            mock_logger = MagicMock()
            with patch('src.rules.getParam', return_value=mock_logger):
                result = await eval_rule(rule, {})
                
                assert result["triggered"] == True
                mock_logger.debug.assert_called_once_with("Time triggered")
    
    async def test_time_rule_outside_range(self):
        """Test time rule evaluation when current time is outside range"""
        rule = RuleTime()
        rule.ranges = [
            TimeRange(start_hour=9, end_hour=17)
        ]
        
        # Mock current time to be 20:00 (8pm) which is outside range
        with patch('src.rules.datetime') as mock_datetime:
            mock_now = MagicMock()
            mock_now.hour = 20
            mock_datetime.now.return_value = mock_now
            
            # Mock logger
            mock_logger = MagicMock()
            with patch('src.rules.getParam', return_value=mock_logger):
                result = await eval_rule(rule, {})
                
                assert result["triggered"] == False
                mock_logger.debug.assert_not_called()
    
    async def test_time_rule_at_range_start(self):
        """Test time rule evaluation when current time is exactly at range start"""
        rule = RuleTime()
        rule.ranges = [
            TimeRange(start_hour=9, end_hour=17)
        ]
        
        # Mock current time to be 9:00 which is at the start of the range
        with patch('src.rules.datetime') as mock_datetime:
            mock_now = MagicMock()
            mock_now.hour = 9
            mock_datetime.now.return_value = mock_now
            
            # Mock logger
            mock_logger = MagicMock()
            with patch('src.rules.getParam', return_value=mock_logger):
                result = await eval_rule(rule, {})
                
                assert result["triggered"] == True
                mock_logger.debug.assert_called_once_with("Time triggered")
    
    async def test_time_rule_at_range_end(self):
        """Test time rule evaluation when current time is exactly at range end"""
        rule = RuleTime()
        rule.ranges = [
            TimeRange(start_hour=9, end_hour=17)
        ]
        
        # Mock current time to be 17:00 which is at the end of the range (exclusive)
        with patch('src.rules.datetime') as mock_datetime:
            mock_now = MagicMock()
            mock_now.hour = 17
            mock_datetime.now.return_value = mock_now
            
            # Mock logger
            mock_logger = MagicMock()
            with patch('src.rules.getParam', return_value=mock_logger):
                result = await eval_rule(rule, {})
                
                assert result["triggered"] == False
                mock_logger.debug.assert_not_called()
    
    async def test_time_rule_multiple_ranges_in_range(self):
        """Test time rule evaluation with multiple ranges when time is in one of them"""
        rule = RuleTime()
        rule.ranges = [
            TimeRange(start_hour=9, end_hour=12),
            TimeRange(start_hour=13, end_hour=17)
        ]
        
        # Mock current time to be 14:00 which is within the second range
        with patch('src.rules.datetime') as mock_datetime:
            mock_now = MagicMock()
            mock_now.hour = 14
            mock_datetime.now.return_value = mock_now
            
            # Mock logger
            mock_logger = MagicMock()
            with patch('src.rules.getParam', return_value=mock_logger):
                result = await eval_rule(rule, {})
                
                assert result["triggered"] == True
                mock_logger.debug.assert_called_once_with("Time triggered")
    
    async def test_time_rule_multiple_ranges_outside_range(self):
        """Test time rule evaluation with multiple ranges when time is outside all of them"""
        rule = RuleTime()
        rule.ranges = [
            TimeRange(start_hour=9, end_hour=12),
            TimeRange(start_hour=13, end_hour=17)
        ]
        
        # Mock current time to be 12:30 which is between the two ranges
        with patch('src.rules.datetime') as mock_datetime:
            mock_now = MagicMock()
            mock_now.hour = 12.5
            mock_datetime.now.return_value = mock_now
            
            # Mock logger
            mock_logger = MagicMock()
            with patch('src.rules.getParam', return_value=mock_logger):
                result = await eval_rule(rule, {})
                
                assert result["triggered"] == False
                mock_logger.debug.assert_not_called()
    
    @pytest.mark.xfail(reason="Current implementation does not properly handle overnight ranges")
    async def test_time_rule_overnight_range(self):
        """Test time rule with overnight range (spanning midnight)"""
        rule = RuleTime()
        rule.ranges = [
            TimeRange(start_hour=22, end_hour=6)  # 10pm to 6am
        ]
        
        # Test at 23:00 (11pm) which is within range
        with patch('src.rules.datetime') as mock_datetime:
            mock_now = MagicMock()
            mock_now.hour = 23
            mock_datetime.now.return_value = mock_now
            
            # Mock logger
            mock_logger = MagicMock()
            with patch('src.rules.getParam', return_value=mock_logger):
                result = await eval_rule(rule, {})
                
                # NOTE: This will fail with the current implementation
                # A proper implementation would need to handle overnight ranges
                assert result["triggered"] == True
                mock_logger.debug.assert_called_once_with("Time triggered")
    
    async def test_time_rule_all_day(self):
        """Test time rule that covers the entire day"""
        rule = RuleTime()
        rule.ranges = [
            TimeRange(start_hour=0, end_hour=24)  # Midnight to midnight
        ]
        
        # Test at various times throughout the day
        for hour in [0, 6, 12, 18, 23]:
            with patch('src.rules.datetime') as mock_datetime:
                mock_now = MagicMock()
                mock_now.hour = hour
                mock_datetime.now.return_value = mock_now
                
                # Mock logger
                mock_logger = MagicMock()
                with patch('src.rules.getParam', return_value=mock_logger):
                    result = await eval_rule(rule, {})
                    
                    assert result["triggered"] == True
                    mock_logger.debug.assert_called_once_with("Time triggered") 