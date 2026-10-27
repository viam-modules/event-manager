from unittest.mock import MagicMock, patch

from src import events
from src.globals import shared_state


def test_backoff_schedule():
    """Test that backoff schedule correctly adjusts pause duration based on continuous triggering"""
    # Create an event with a backoff schedule
    event = events.Event(
        name="test_backoff",
        pause_alerting_on_event_secs=60,  # Base pause duration
        backoff_schedule={
            300: 120,  # After 5 minutes, pause for 2 minutes
            1200: 300,  # After 20 minutes, pause for 5 minutes
            3600: 900,  # After 1 hour, pause for 15 minutes
        },
    )

    # Initial state
    assert event.pause_alerting_on_event_secs == 60  # Base value unchanged
    assert event.backoff_adjustment == 0  # No adjustment initially
    assert event.get_effective_pause_duration() == 60  # Effective duration is base value
    assert event.continuous_trigger_start_time == 0  # No continuous trigger yet

    # Simulate first trigger
    event.is_triggered = True
    event.last_triggered = 1000
    event.continuous_trigger_start_time = 1000  # First trigger in sequence

    # Test at 4 minutes (should still be default)
    event.last_triggered = 1240  # 1000 + 240 seconds
    event._check_backoff_schedule(1240)
    assert event.pause_alerting_on_event_secs == 60  # Base value unchanged
    assert event.backoff_adjustment == 0  # No adjustment yet
    assert event.get_effective_pause_duration() == 60  # Effective duration is base value

    # Test at 6 minutes (should be 120)
    event.last_triggered = 1360  # 1000 + 360 seconds
    event._check_backoff_schedule(1360)
    assert event.pause_alerting_on_event_secs == 60  # Base value unchanged
    assert event.backoff_adjustment == 60  # 120 - 60 = 60
    assert event.get_effective_pause_duration() == 120  # Effective duration is 120

    # Test at 25 minutes (should be 300)
    event.last_triggered = 2500  # 1000 + 1500 seconds
    event._check_backoff_schedule(2500)
    assert event.pause_alerting_on_event_secs == 60  # Base value unchanged
    assert event.backoff_adjustment == 240  # 300 - 60 = 240
    assert event.get_effective_pause_duration() == 300  # Effective duration is 300

    # Test at 1 hour+ (should be 900)
    event.last_triggered = 8200  # 1000 + 7200 seconds
    event._check_backoff_schedule(8200)
    assert event.pause_alerting_on_event_secs == 60  # Base value unchanged
    assert event.backoff_adjustment == 840  # 900 - 60 = 840
    assert event.get_effective_pause_duration() == 900  # Effective duration is 900

    # Test reset when event is no longer triggered
    event.is_triggered = False
    event.continuous_trigger_start_time = 0
    event.backoff_adjustment = 0
    assert event.get_effective_pause_duration() == 60  # Back to base duration


def test_backoff_schedule_logs_adjustment():
    """A backoff adjustment is logged at debug level through the shared logger"""
    event = events.Event(name="test_backoff_log", pause_alerting_on_event_secs=60, backoff_schedule={300: 120})
    event.continuous_trigger_start_time = 1000
    logger = MagicMock()

    with patch.dict(shared_state, {"logger": logger}):
        event._check_backoff_schedule(1360)

    assert event.backoff_adjustment == 60
    logger.debug.assert_called_once()
    assert "Pause duration adjusted to 120s" in logger.debug.call_args.args[0]
