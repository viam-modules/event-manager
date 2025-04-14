# Security Event Manager Tests

This directory contains automated tests for the Security Event Manager project.

## Test Organization

All tests use the pytest framework:

- `test_events.py`: Tests for the Event class functionality
- `test_rules.py`: Tests for the rule classes (RuleDetector, RuleClassifier, RuleTime, etc.)
- `test_event_manager.py`: Tests for the eventManager class
- `test_notifications.py`: Tests for the notification classes and notification functionality
- `test_rules_evaluation.py`: Comprehensive tests for rule evaluation logic with mocks
- `test_classifier_rules.py`: Tests for classifier rule evaluation and error handling
- `test_tracker_rules.py`: Tests for tracker rule evaluation
- `test_logic.py`: Tests for logical functions (AND, OR, XOR, etc.)

## Running Tests

There are several ways to run the tests:

### Using Make

The project includes several make targets for testing:

```bash
# Run all tests
make test

# Run individual test files separately
make test-individual

# Run tests with coverage reporting
make coverage
```

### Running Directly

You can also run the tests directly:

```bash
# Run all tests
pytest -xvs tests/ --asyncio-mode=auto

# Run tests with verbose output
pytest -xvs tests/ --asyncio-mode=auto

# Run specific test files
pytest -xvs tests/test_notifications.py --asyncio-mode=auto
pytest -xvs tests/test_event_manager.py --asyncio-mode=auto

# Run specific test classes or methods
pytest -xvs tests/test_notifications.py::TestNotificationClasses --asyncio-mode=auto
pytest -xvs tests/test_notifications.py::TestNotify::test_notify_webhook --asyncio-mode=auto

# Run tests matching a specific pattern
pytest -xvs tests/ -k "webhook" --asyncio-mode=auto
```

## Test Dependencies

The tests require the following packages, which should be installed in your virtual environment:
- pytest
- pytest-asyncio
- pytest-cov
- coverage

These can be installed via:
```bash
make install-test-deps
```
or directly with:
```bash
pip install -r tests/requirements-test.txt
```

## Adding More Tests

When adding new tests:
1. Create a new test file in the `tests/` directory named `test_*.py`
2. Follow the patterns established in existing test files
3. Use appropriate pytest fixtures and decorators
4. Use `@pytest.mark.asyncio` for testing async functions

## Mock Strategy

For testing components that interact with external services:
1. Use `unittest.mock.patch` to replace external dependencies
2. Create `MagicMock` and `AsyncMock` objects to simulate responses
3. For image processing functions, mock the `viam_to_pil_image` function to avoid errors
4. Use pytest fixtures to provide common mock objects
