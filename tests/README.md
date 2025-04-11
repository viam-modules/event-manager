# Security Event Manager Tests

This directory contains automated tests for the Security Event Manager project.

## Test Organization

- `test_events.py`: Tests for the Event class functionality
- `test_rules.py`: Tests for the rule classes (RuleDetector, RuleClassifier, RuleTime, etc.)
- `test_event_manager.py`: Tests for the eventManager class
- `test_notifications.py`: Tests for the notification classes (NotificationEmail, NotificationSMS, etc.)
- `test_pytest.py`: Tests using pytest framework
- `test_rules_evaluation.py`: Comprehensive tests for rule evaluation logic with mocks
- `test_classifier_rules.py`: Tests for classifier rule evaluation and error handling
- `test_logic.py`: Tests for logical functions (AND, OR, XOR, etc.)
- `run_tests.py`: Script to run all the unittest-based tests

## Running Tests

There are several ways to run the tests:

### Using Make

The project includes several make targets for testing:

```bash
# Run all unittest tests
make test

# Run individual unittest test files
make test-individual

# Run pytest tests
make pytest

# Run tests with coverage reporting (unittest)
make coverage

# Run tests with coverage reporting (pytest)
make coverage-pytest
```

### Running Directly

You can also run the tests directly:

```bash
# Run all unittest tests
python -m tests.run_tests

# Run individual test files
python -m unittest tests.test_events
python -m unittest tests.test_rules
python -m unittest tests.test_event_manager
python -m unittest tests.test_notifications
python -m unittest tests.test_rules_evaluation
python -m unittest tests.test_classifier_rules
python -m unittest tests.test_logic

# Run pytest tests
pytest -xvs tests/
```

## Coverage Reports

Coverage reports are generated when running the coverage commands (`make coverage` or `make coverage-pytest`). The HTML report is generated in the `htmlcov/` directory.

After adding our comprehensive tests, we've achieved:
- 100% test coverage for `src/logic.py` 
- 100% test coverage for `src/notificationClass.py`
- 96% test coverage for `src/rules.py` (up from the initial 37%)
- 69% overall coverage (up from 41%)

## Test Dependencies

The tests require the following packages, which should be installed in your virtual environment:
- coverage
- pytest

These can be installed via `pip install -r requirements.txt`.

## Adding More Tests

When adding new tests:
1. Create a new test file in the `tests/` directory
2. Follow the patterns established in existing test files
3. Update `run_tests.py` if using unittest
4. Use appropriate naming conventions (`test_*.py` for pytest files)

## Mock Strategy

For testing components that interact with external services:
1. Use `unittest.mock.patch` to replace external dependencies
2. Create `MagicMock` and `AsyncMock` objects to simulate responses
3. For image processing functions, mock the `viam_to_pil_image` function to avoid errors

## Areas for Further Testing

While we've significantly improved test coverage, the following areas could use additional testing:
- `src/eventManager.py` (17% coverage)
- `src/notifications.py` (16% coverage)
- `src/triggered.py` (22% coverage)
- `src/actions.py` (38% coverage)
- `src/resourceUtils.py` (25% coverage) 