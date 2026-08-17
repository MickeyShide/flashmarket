"""Contracts for the shared FlashMarket RabbitMQ virtual host."""

from __future__ import annotations

import importlib.util
import json
import os
import urllib.error
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SHARED_RABBITMQ_PATH = "/flashmarket"

WORKFLOWS = (
    "auth-deploy.yml",
    "catalog-deploy.yml",
    "drops-deploy.yml",
    "inventory-deploy.yml",
    "notifications-deploy.yml",
    "orders-deploy.yml",
    "payments-deploy.yml",
    "wishlist-deploy.yml",
)

EXAMPLES = (
    "auth/.env.example",
    "auth/.env.deploy.example",
    "catalog/.env.example",
    "catalog/.env.deploy.example",
    "drops/.env.example",
    "inventory/.env.example",
    "inventory/.env.deploy.example",
    "notifications/.env.example",
    "notifications/.env.deploy.example",
    "orders/.env.example",
    "orders/.env.deploy.example",
    "payments/.env.example",
    "payments/.env.deploy.example",
)

RUNTIME_CONFIGURATION = (
    "auth/src/auth_service/config.py",
    "drops/src/drops/config.py",
    "inventory/src/inventory/config.py",
    "notifications/src/notifications/config.py",
    "orders/src/orders/config.py",
    "payments/src/payments/config.py",
    "wishlist/src/wishlist/config.py",
    "auth/docker-compose.yml",
    "drops/docker-compose.yml",
    "inventory/docker-compose.yml",
    "notifications/docker-compose.yml",
    "orders/docker-compose.yml",
    "payments/docker-compose.yml",
    "wishlist/docker-compose.yml",
)


def _load_init_infra() -> ModuleType:
    path = PROJECT_ROOT / "docker" / "init-infra.py"
    spec = importlib.util.spec_from_file_location("flashmarket_init_infra", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_all_production_workflows_use_shared_vhost() -> None:
    for workflow_name in WORKFLOWS:
        content = (PROJECT_ROOT / ".github" / "workflows" / workflow_name).read_text(
            encoding="utf-8"
        )
        rabbitmq_lines = [
            line for line in content.splitlines() if "RABBITMQ_URL=" in line
        ]
        assert rabbitmq_lines, f"{workflow_name} does not render a RabbitMQ URL"
        assert all(SHARED_RABBITMQ_PATH in line for line in rabbitmq_lines), (
            workflow_name
        )


def test_all_environment_examples_use_shared_vhost() -> None:
    for relative_path in EXAMPLES:
        content = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
        rabbitmq_lines = [
            line for line in content.splitlines() if "RABBITMQ_URL=" in line
        ]
        assert rabbitmq_lines, f"{relative_path} does not define a RabbitMQ URL"
        assert all(SHARED_RABBITMQ_PATH in line for line in rabbitmq_lines), (
            relative_path
        )


def test_runtime_defaults_and_local_compose_use_shared_vhost() -> None:
    for relative_path in RUNTIME_CONFIGURATION:
        content = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
        rabbitmq_lines = [
            line
            for line in content.splitlines()
            if "rabbitmq_url: str =" in line.lower() or "RABBITMQ_URL:" in line
        ]
        assert rabbitmq_lines, f"{relative_path} does not define a RabbitMQ URL"
        assert all(SHARED_RABBITMQ_PATH in line for line in rabbitmq_lines), (
            relative_path
        )


def test_amqp_uri_maps_to_exactly_one_vhost() -> None:
    module = _load_init_infra()

    assert module._rabbitmq_vhost_from_url(
        "amqp://user:pass@rabbitmq:5672/flashmarket"
    ) == ("flashmarket")
    assert module._rabbitmq_vhost_from_url("amqp://user:pass@rabbitmq:5672/%2F") == "/"
    assert module._rabbitmq_vhost_from_url("amqp://user:pass@rabbitmq:5672/") == "/"


def test_wishlist_rabbitmq_url_is_discovered() -> None:
    module = _load_init_infra()
    url = "amqp://user:pass@rabbitmq:5672/flashmarket"

    with patch.dict(os.environ, {"WISHLIST_RABBITMQ_URL": url}, clear=True):
        assert module._get_rabbitmq_urls() == [url]


def test_celery_broker_url_is_discovered() -> None:
    module = _load_init_infra()
    url = "amqp://user:pass@rabbitmq:5672/flashmarket-tasks"

    with patch.dict(os.environ, {"CELERY_BROKER_URL": url}, clear=True):
        assert module._get_celery_broker_urls() == [url]


def test_celery_task_vhost_bootstrap_skips_event_topology() -> None:
    module = _load_init_infra()
    requests: list[object] = []

    class Response:
        status = 201

        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    def capture(request, *, timeout: float):
        assert timeout == 10.0
        requests.append(request)
        return Response()

    with (
        patch.object(module, "resolve_host_ipv4", return_value="127.0.0.1"),
        patch.object(module.urllib.request, "urlopen", side_effect=capture),
    ):
        module._ensure_vhost_and_permissions(
            "amqp://user:pass@rabbitmq:5672/flashmarket-tasks",
            install_event_topology=False,
        )

    urls = [request.full_url for request in requests]
    assert len(urls) == 2
    assert urls[0].endswith("/vhosts/flashmarket-tasks")
    assert urls[1].endswith("/permissions/flashmarket-tasks/user")


def test_vhost_bootstrap_failure_is_fatal() -> None:
    module = _load_init_infra()
    error = urllib.error.URLError("management API unavailable")

    with (
        patch.object(module, "resolve_host_ipv4", return_value="127.0.0.1"),
        patch.object(module.urllib.request, "urlopen", side_effect=error),
        pytest.raises(urllib.error.URLError),
    ):
        module._ensure_vhost_and_permissions(
            "amqp://user:pass@rabbitmq:5672/flashmarket"
        )


def test_bootstrap_declares_reliability_exchanges_and_queue_policies() -> None:
    module = _load_init_infra()
    requests: list[object] = []

    class Response:
        status = 201

        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    def capture(request, *, timeout: float):
        assert timeout == 10.0
        requests.append(request)
        return Response()

    with (
        patch.object(module, "resolve_host_ipv4", return_value="127.0.0.1"),
        patch.object(module.urllib.request, "urlopen", side_effect=capture),
    ):
        module._ensure_vhost_and_permissions(
            "amqp://user:pass@rabbitmq:5672/flashmarket"
        )

    urls = [request.full_url for request in requests]
    assert any("/exchanges/flashmarket/flashmarket.retry" in url for url in urls)
    assert any("/exchanges/flashmarket/flashmarket.dead-letter" in url for url in urls)
    dlq_requests = [
        request for request in requests if "/queues/flashmarket/" in request.full_url
    ]
    binding_requests = [
        request
        for request in requests
        if "/bindings/flashmarket/e/" in request.full_url
    ]
    assert len(dlq_requests) == 5
    assert len(binding_requests) == 5
    assert all(request.get_method() == "POST" for request in binding_requests)
    policies = [
        request for request in requests if "/policies/flashmarket/" in request.full_url
    ]
    assert len(policies) == 15
    payloads = [json.loads(request.data) for request in policies]
    main = [
        payload["definition"]
        for payload in payloads
        if payload["definition"]["overflow"] == "reject-publish-dlx"
    ]
    bounded = [
        payload["definition"]
        for payload in payloads
        if payload["definition"]["overflow"] == "reject-publish"
    ]
    assert len(main) == 5
    assert len(bounded) == 10
    assert all(definition["overflow"] == "reject-publish-dlx" for definition in main)
    assert all(
        definition["dead-letter-exchange"] == "flashmarket.dead-letter"
        for definition in main
    )
