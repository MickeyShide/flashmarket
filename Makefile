UV ?= uv
TEST_RUNNER := scripts/test_runner.py

.PHONY: help test test-e2e test-all test-service openapi frontend-build

help:
	@$(UV) run python $(TEST_RUNNER) help

test:
	@$(UV) run python $(TEST_RUNNER) test

test-e2e:
	@$(UV) run python $(TEST_RUNNER) test-e2e

test-all:
	@$(UV) run python $(TEST_RUNNER) test-all

test-service:
	@$(UV) run python $(TEST_RUNNER) test-service --service "$(SERVICE)"

openapi:
	@python tools/openapi/generate.py

frontend-build: openapi
	@cd frontend && npm run build
