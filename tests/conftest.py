import pytest
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
import asyncio

# Add the source directory to the path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent))

# Remove the custom event_loop fixture and let pytest-asyncio handle it
# @pytest.fixture
# def event_loop():
#     """Create an instance of the default event loop for each test case."""
#     loop = asyncio.get_event_loop_policy().new_event_loop()
#     yield loop
#     loop.close()

@pytest.fixture
def mock_logger():
    """Return a mock logger for testing."""
    logger = MagicMock()
    return logger

@pytest.fixture
def mock_resources():
    """Return mock resources for testing."""
    return {"_deps": {}}

@pytest.fixture
def mock_vision_service():
    """Return a mock vision service for testing."""
    service = AsyncMock()
    return service

@pytest.fixture
def mock_image():
    """Return a mock PIL image for testing."""
    image = MagicMock()
    image.crop.return_value = MagicMock()
    return image

# Mock for regex substitution used in tracker rules
@pytest.fixture
def mock_regex_sub():
    """Mock function for re.sub that handles tracker label stripping."""
    def _sub_side_effect(pattern, replacement, string):
        if '(label:' in string:
            return string.split('(label:')[0].strip()
        return string
    return _sub_side_effect 