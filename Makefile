.PHONY: build run test test-individual coverage install-test-deps

build:
	sh build.sh
run:
	./dist/main
install-test-deps:
	pip install -r tests/requirements-test.txt
test: install-test-deps
	pytest -xvs tests/
test-individual: install-test-deps
	pytest -xvs tests/test_events.py
	pytest -xvs tests/test_rules.py
	pytest -xvs tests/test_event_manager.py
	pytest -xvs tests/test_notifications.py
coverage: install-test-deps
	python -m coverage run -m pytest tests/
	python -m coverage report
	python -m coverage html