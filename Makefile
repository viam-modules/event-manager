build:
	sh build.sh
run:
	./dist/main
install-test-deps:
	pip install -r tests/requirements-test.txt
test: install-test-deps
	pytest -xvs tests/ --asyncio-mode=auto
test-individual: install-test-deps
	pytest -xvs tests/test_events.py --asyncio-mode=auto
	pytest -xvs tests/test_rules.py --asyncio-mode=auto
	pytest -xvs tests/test_event_manager.py --asyncio-mode=auto
	pytest -xvs tests/test_notifications.py --asyncio-mode=auto
coverage: install-test-deps
	python -m coverage run -m pytest tests/ --asyncio-mode=auto
	python -m coverage report
	python -m coverage html