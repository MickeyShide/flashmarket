UV ?= uv
TEST_RUNNER := scripts/test_runner.py
COMPOSE := docker compose
OBSERVABILITY_NETWORK ?= shide-observability
OBSERVABILITY_LOG_VOLUME ?= shide-backend-logs-local
OBSERVABILITY_INFRA ?= shide-postgres shide-redis shide-rabbitmq shide-minio
MEDIA_S3_BUCKET ?= flashmarket-public

.DEFAULT_GOAL := help

.PHONY: help check observability-check up down restart logs ps test test-e2e test-all test-service openapi frontend-build

ifeq ($(OS),Windows_NT)
SHELL := powershell.exe
.SHELLFLAGS := -NoProfile -Command

check:
	@if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { Write-Error "Docker CLI is not installed or is not in PATH"; exit 1 }; docker compose version *> $$null; if ($$LASTEXITCODE -ne 0) { Write-Error "Docker Compose is not available"; exit 1 }; docker info *> $$null; if ($$LASTEXITCODE -ne 0) { Write-Error "Docker daemon is not running"; exit 1 }

observability-check: check
	@docker network inspect "$(OBSERVABILITY_NETWORK)" *> $$null; if ($$LASTEXITCODE -ne 0) { Write-Error "Docker network '$(OBSERVABILITY_NETWORK)' is missing. Start shide-observability separately, then retry."; exit 1 }
	@docker volume inspect "$(OBSERVABILITY_LOG_VOLUME)" *> $$null; if ($$LASTEXITCODE -ne 0) { Write-Error "Docker volume '$(OBSERVABILITY_LOG_VOLUME)' is missing. Start shide-observability separately, then retry."; exit 1 }
	@$$required = "$(OBSERVABILITY_INFRA)".Split(" ", [System.StringSplitOptions]::RemoveEmptyEntries); foreach ($$container in $$required) { $$rawState = docker inspect --format '{{json .State}}' "$$container" 2>$$null; if ($$LASTEXITCODE -ne 0) { Write-Error "Required container '$$container' is missing. Start shide-observability separately, then retry."; exit 1 }; $$state = $$rawState | ConvertFrom-Json; if ($$state.Status -ne "running") { Write-Error "Required container '$$container' is '$$($$state.Status)', expected 'running'. Start shide-observability separately, then retry."; exit 1 }; if ($$null -ne $$state.Health -and $$state.Health.Status -ne "healthy") { Write-Error "Required container '$$container' is '$$($$state.Health.Status)', expected 'healthy'. Wait for shide-observability to become ready, then retry."; exit 1 } }; Write-Host "shide-observability is ready"

up: observability-check
	@function Get-ContainerEnv([string] $$container, [string] $$name) { $$prefix = "$$name="; $$line = docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$$container" | Where-Object { $$_.StartsWith($$prefix) } | Select-Object -First 1; if (-not $$line) { throw "Required environment variable '$$name' is missing from '$$container'" }; return $$line.Substring($$prefix.Length) }; $$infraUser = Get-ContainerEnv "shide-postgres" "POSTGRES_USER"; $$rabbitUser = Get-ContainerEnv "shide-rabbitmq" "RABBITMQ_DEFAULT_USER"; if ($$infraUser -ne $$rabbitUser) { throw "PostgreSQL and RabbitMQ must use the same shared infrastructure user" }; $$env:INFRA_USER = $$infraUser; $$env:POSTGRES_PASSWORD = Get-ContainerEnv "shide-postgres" "POSTGRES_PASSWORD"; $$env:RABBITMQ_PASSWORD = Get-ContainerEnv "shide-rabbitmq" "RABBITMQ_DEFAULT_PASS"; $$env:S3_ACCESS_KEY = Get-ContainerEnv "shide-minio" "MINIO_ROOT_USER"; $$env:S3_SECRET_KEY = Get-ContainerEnv "shide-minio" "MINIO_ROOT_PASSWORD"; $$env:MEDIA_S3_BUCKET = "$(MEDIA_S3_BUCKET)"; docker exec shide-minio mc alias set flashmarket-local http://localhost:9000 "$$env:S3_ACCESS_KEY" "$$env:S3_SECRET_KEY" *> $$null; if ($$LASTEXITCODE -ne 0) { throw "Could not connect to the shared MinIO instance" }; docker exec shide-minio mc mb --ignore-existing "flashmarket-local/$(MEDIA_S3_BUCKET)" *> $$null; if ($$LASTEXITCODE -ne 0) { throw "Could not prepare the FlashMarket media bucket" }; docker exec shide-minio mc anonymous set download "flashmarket-local/$(MEDIA_S3_BUCKET)" *> $$null; if ($$LASTEXITCODE -ne 0) { throw "Could not configure public media downloads" }; $$helperImage = docker inspect --format '{{.Config.Image}}' shide-postgres; docker run --rm --user 0:0 --volume "$(OBSERVABILITY_LOG_VOLUME):/var/log/shide" --entrypoint chown "$$helperImage" -R 999:999 /var/log/shide *> $$null; if ($$LASTEXITCODE -ne 0) { throw "Could not prepare the shared observability log volume" }; $(COMPOSE) up -d --build --wait; if ($$LASTEXITCODE -ne 0) { $$code = $$LASTEXITCODE; Write-Error "FlashMarket failed to reach running/healthy state"; $(COMPOSE) ps; exit $$code }
else
SHELL := /bin/sh
.SHELLFLAGS := -eu -c

check:
	@command -v docker >/dev/null 2>&1 || { echo "Docker CLI is not installed or is not in PATH" >&2; exit 1; }
	@docker compose version >/dev/null 2>&1 || { echo "Docker Compose is not available" >&2; exit 1; }
	@docker info >/dev/null 2>&1 || { echo "Docker daemon is not running" >&2; exit 1; }

observability-check: check
	@docker network inspect "$(OBSERVABILITY_NETWORK)" >/dev/null 2>&1 || { echo "Docker network '$(OBSERVABILITY_NETWORK)' is missing. Start shide-observability separately, then retry." >&2; exit 1; }
	@docker volume inspect "$(OBSERVABILITY_LOG_VOLUME)" >/dev/null 2>&1 || { echo "Docker volume '$(OBSERVABILITY_LOG_VOLUME)' is missing. Start shide-observability separately, then retry." >&2; exit 1; }
	@for container in $(OBSERVABILITY_INFRA); do \
		status=$$(docker inspect --format '{{.State.Status}}' "$$container" 2>/dev/null) || { echo "Required container '$$container' is missing. Start shide-observability separately, then retry." >&2; exit 1; }; \
		[ "$$status" = "running" ] || { echo "Required container '$$container' is '$$status', expected 'running'. Start shide-observability separately, then retry." >&2; exit 1; }; \
		health=$$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$$container"); \
		[ "$$health" = "none" ] || [ "$$health" = "healthy" ] || { echo "Required container '$$container' is '$$health', expected 'healthy'. Wait for shide-observability to become ready, then retry." >&2; exit 1; }; \
	done
	@echo "shide-observability is ready"

up: observability-check
	@get_container_env() { docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$$1" | sed -n "s/^$$2=//p" | head -n 1; }; \
	infra_user=$$(get_container_env shide-postgres POSTGRES_USER); \
	rabbit_user=$$(get_container_env shide-rabbitmq RABBITMQ_DEFAULT_USER); \
	[ -n "$$infra_user" ] || { echo "POSTGRES_USER is missing from shide-postgres" >&2; exit 1; }; \
	[ "$$infra_user" = "$$rabbit_user" ] || { echo "PostgreSQL and RabbitMQ must use the same shared infrastructure user" >&2; exit 1; }; \
	POSTGRES_PASSWORD=$$(get_container_env shide-postgres POSTGRES_PASSWORD); \
	RABBITMQ_PASSWORD=$$(get_container_env shide-rabbitmq RABBITMQ_DEFAULT_PASS); \
	S3_ACCESS_KEY=$$(get_container_env shide-minio MINIO_ROOT_USER); \
	S3_SECRET_KEY=$$(get_container_env shide-minio MINIO_ROOT_PASSWORD); \
	[ -n "$$POSTGRES_PASSWORD" ] && [ -n "$$RABBITMQ_PASSWORD" ] && [ -n "$$S3_ACCESS_KEY" ] && [ -n "$$S3_SECRET_KEY" ] || { echo "Required shared infrastructure credentials are missing" >&2; exit 1; }; \
	MEDIA_S3_BUCKET="$(MEDIA_S3_BUCKET)"; \
	export INFRA_USER="$$infra_user" POSTGRES_PASSWORD RABBITMQ_PASSWORD S3_ACCESS_KEY S3_SECRET_KEY MEDIA_S3_BUCKET; \
	docker exec shide-minio mc alias set flashmarket-local http://localhost:9000 "$$S3_ACCESS_KEY" "$$S3_SECRET_KEY" >/dev/null || { echo "Could not connect to the shared MinIO instance" >&2; exit 1; }; \
	docker exec shide-minio mc mb --ignore-existing "flashmarket-local/$$MEDIA_S3_BUCKET" >/dev/null || { echo "Could not prepare the FlashMarket media bucket" >&2; exit 1; }; \
	docker exec shide-minio mc anonymous set download "flashmarket-local/$$MEDIA_S3_BUCKET" >/dev/null || { echo "Could not configure public media downloads" >&2; exit 1; }; \
	helper_image=$$(docker inspect --format '{{.Config.Image}}' shide-postgres); \
	docker run --rm --user 0:0 --volume "$(OBSERVABILITY_LOG_VOLUME):/var/log/shide" --entrypoint chown "$$helper_image" -R 999:999 /var/log/shide >/dev/null || { echo "Could not prepare the shared observability log volume" >&2; exit 1; }; \
	$(COMPOSE) up -d --build --wait || { code=$$?; echo "FlashMarket failed to reach running/healthy state" >&2; $(COMPOSE) ps; exit $$code; }
endif

help:
	@echo "Available stack commands:"
	@echo "  make up       Check observability, build, and start all FlashMarket services"
	@echo "  make down     Stop FlashMarket without touching shared infrastructure"
	@echo "  make restart  Restart the complete FlashMarket stack"
	@echo "  make logs     Follow logs from all FlashMarket services"
	@echo "  make ps       Show FlashMarket service status"
	@echo ""
	@$(UV) run python $(TEST_RUNNER) help

down: check
	@$(COMPOSE) down

restart: down
	@$(MAKE) up

logs: check
	@$(COMPOSE) logs -f --tail=100

ps: check
	@$(COMPOSE) ps

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
