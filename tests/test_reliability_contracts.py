"""Deployment and alerting contracts for background-worker reliability."""

from __future__ import annotations

from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent

BACKGROUND: dict[str, set[str]] = {
    "auth/docker-compose.deploy.yml": {"maintenance", "outbox"},
    "inventory/docker-compose.deploy.yml": {"consumer", "outbox", "maintenance"},
    "orders/docker-compose.deploy.yml": {"consumer", "outbox"},
    "payments/docker-compose.deploy.yml": {"consumer", "outbox"},
    "notifications/docker-compose.deploy.yml": {"consumer", "outbox"},
    "wishlist/docker-compose.deploy.yml": {"consumer", "outbox"},
    "drops/docker-compose.deploy.yml": {"maintenance", "outbox"},
    "media/docker-compose.deploy.yml": {"maintenance"},
}

OUTBOX_WORKERS = (
    "auth/src/auth_service/outbox_worker.py",
    "inventory/src/inventory/outbox_worker.py",
    "orders/src/orders/outbox_worker.py",
    "payments/src/payments/outbox_worker.py",
    "notifications/src/notifications/outbox_worker.py",
    "wishlist/src/wishlist/outbox_worker.py",
    "drops/src/drops/outbox_worker.py",
)


def _load(path: str) -> dict:
    return yaml.safe_load((PROJECT_ROOT / path).read_text(encoding="utf-8"))


def test_production_background_services_are_healthy_and_watchdog_opted_in() -> None:
    for path, names in BACKGROUND.items():
        services = _load(path)["services"]
        for name in names:
            service = services[name]
            label = f"{path}:{name}"
            assert service.get("healthcheck", {}).get("test"), label
            assert service.get("labels", {}).get("flashmarket.autoheal") == "true", (
                label
            )


def test_outbox_workers_keep_heartbeat_alive_while_connected() -> None:
    for path in OUTBOX_WORKERS:
        source = (PROJECT_ROOT / path).read_text(encoding="utf-8")
        assert "async with periodic_heartbeat(" in source, path
        assert (
            "interval_seconds=settings.worker_heartbeat_interval_seconds" in source
        ), path
        assert "touch_heartbeat(" not in source, path


def test_deployed_worker_heartbeat_probes_allow_python_startup_time() -> None:
    for worker_path in OUTBOX_WORKERS:
        service = worker_path.split("/", maxsplit=1)[0]
        compose_path = PROJECT_ROOT / service / "docker-compose.deploy.yml"
        compose = compose_path.read_text(encoding="utf-8")
        heartbeat = compose.index("rabbitmq_reliability.heartbeat")
        worker_healthcheck = compose[heartbeat : heartbeat + 300]

        assert "timeout: 10s" in worker_healthcheck, compose_path


def test_reliability_alert_rules_have_unique_names_and_runbooks() -> None:
    payload = _load("deploy/prometheus/flashmarket-reliability.rules.yml")
    rules = [rule for group in payload["groups"] for rule in group["rules"]]
    alert_names = [rule["alert"] for rule in rules]
    assert len(alert_names) == len(set(alert_names))
    assert {
        "FlashMarketRabbitMQDLQNotEmpty",
        "FlashMarketRabbitMQConsumerMissing",
        "FlashMarketRabbitMQResourceAlarm",
        "FlashMarketWorkerHeartbeatStale",
        "FlashMarketOutboxBacklogOld",
    } <= set(alert_names)
    for rule in rules:
        assert rule.get("expr"), rule["alert"]
        assert rule.get("labels", {}).get("severity") in {"warning", "critical"}
        assert rule.get("annotations", {}).get("summary")


def test_watchdog_systemd_unit_is_rate_limited_and_hardened() -> None:
    service = (
        PROJECT_ROOT / "deploy/systemd/flashmarket-worker-watchdog.service"
    ).read_text(encoding="utf-8")
    timer = (
        PROJECT_ROOT / "deploy/systemd/flashmarket-worker-watchdog.timer"
    ).read_text(encoding="utf-8")
    assert "NoNewPrivileges=true" in service
    assert "ProtectSystem=strict" in service
    assert "OnUnitActiveSec=1min" in timer


def test_worker_metrics_targets_match_unique_production_aliases() -> None:
    scrape = _load("deploy/prometheus/scrape-config.example.yml")
    worker_job = next(
        job
        for job in scrape["scrape_configs"]
        if job["job_name"] == "flashmarket-workers"
    )
    targets = {
        target.split(":", 1)[0] for target in worker_job["static_configs"][0]["targets"]
    }
    aliases: set[str] = set()
    for path, names in BACKGROUND.items():
        services = _load(path)["services"]
        for name in names:
            service_aliases = service_network = services[name]["networks"]["backend"][
                "aliases"
            ]
            assert len(service_aliases) == 1, f"{path}:{name}"
            aliases.update(service_network)
    assert targets == aliases
