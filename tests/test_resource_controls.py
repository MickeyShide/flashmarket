"""Contracts for production container resource isolation."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent

COMPOSE_SERVICES: dict[str, set[str]] = {
    "auth/docker-compose.deploy.yml": {"api", "nginx", "maintenance", "beat", "outbox"},
    "catalog/docker-compose.deploy.yml": {"api", "nginx"},
    "inventory/docker-compose.deploy.yml": {"api", "consumer", "outbox", "maintenance", "nginx"},
    "orders/docker-compose.deploy.yml": {"api", "consumer", "outbox", "nginx"},
    "payments/docker-compose.deploy.yml": {"api", "consumer", "outbox", "nginx"},
    "notifications/docker-compose.deploy.yml": {"api", "consumer", "outbox", "nginx"},
    "wishlist/docker-compose.deploy.yml": {"api", "consumer"},
    "drops/docker-compose.deploy.yml": {"api", "maintenance", "outbox"},
    "media/docker-compose.deploy.yml": {"api", "maintenance"},
    "docker-compose.prod.yml": {"gateway", "frontend"},
}

OBSERVABILITY_MODULES = (
    "auth/src/auth_service/observability.py",
    "catalog/src/catalog/observability.py",
    "inventory/src/inventory/observability.py",
    "orders/src/orders/observability.py",
    "payments/src/payments/observability.py",
    "notifications/src/notifications/observability.py",
    "wishlist/src/wishlist/observability.py",
    "drops/src/drops/observability.py",
    "media/src/media_service/observability.py",
)

SIZE_PATTERN = re.compile(r"^(\d+)([kmgt]?)b?$", re.IGNORECASE)
SIZE_MULTIPLIERS = {"": 1, "k": 1024, "m": 1024**2, "g": 1024**3, "t": 1024**4}


def _load(relative_path: str) -> dict:
    return yaml.safe_load((PROJECT_ROOT / relative_path).read_text(encoding="utf-8"))


def _default_value(value: object) -> str:
    text = str(value)
    match = re.fullmatch(r"\$\{[^}:]+:-([^}]+)}", text)
    return match.group(1) if match else text


def _bytes(value: object) -> int:
    normalized = _default_value(value).strip().lower()
    match = SIZE_PATTERN.fullmatch(normalized)
    assert match is not None, f"Invalid memory size: {value}"
    amount, suffix = match.groups()
    return int(amount) * SIZE_MULTIPLIERS[suffix]


def test_all_long_running_production_services_have_resource_guards() -> None:
    for relative_path, expected_services in COMPOSE_SERVICES.items():
        services = _load(relative_path)["services"]
        assert expected_services <= services.keys(), relative_path
        for service_name in expected_services:
            service = services[service_name]
            label = f"{relative_path}:{service_name}"
            assert _bytes(service.get("mem_limit")) > 0, label
            assert _bytes(service.get("mem_reservation")) > 0, label
            assert _bytes(service["mem_reservation"]) <= _bytes(service["mem_limit"]), label
            assert int(_default_value(service.get("pids_limit"))) > 0, label
            assert service.get("init") is True, label
            assert service.get("restart") == "unless-stopped", label
            assert service.get("stop_grace_period"), label
            logging = service.get("logging", {})
            assert logging.get("driver") == "json-file", label
            assert logging.get("options") == {"max-size": "10m", "max-file": "3"}, label


def test_memory_class_defaults_preserve_service_priority() -> None:
    auth = _load("auth/docker-compose.deploy.yml")["services"]["api"]
    catalog = _load("catalog/docker-compose.deploy.yml")["services"]["api"]
    media = _load("media/docker-compose.deploy.yml")["services"]["api"]

    assert _bytes(auth["mem_limit"]) >= _bytes(catalog["mem_limit"])
    assert _bytes(media["mem_limit"]) > _bytes(auth["mem_limit"])


def test_file_logging_is_rotated_in_every_service() -> None:
    for relative_path in OBSERVABILITY_MODULES:
        content = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
        assert "RotatingFileHandler" in content, relative_path
        assert "maxBytes=10 * 1024 * 1024" in content, relative_path
        assert "backupCount=3" in content, relative_path
