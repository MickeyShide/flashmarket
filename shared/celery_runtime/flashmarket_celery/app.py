"""Celery application factory and task routing."""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from typing import Any

from celery import Celery
from kombu import Queue

QUEUES = (
    "auth.maintenance",
    "inventory.maintenance",
    "drops.maintenance",
    "media.maintenance",
)

TASK_ROUTES = {
    "flashmarket.auth.cleanup_expired_data": {"queue": "auth.maintenance"},
    "flashmarket.inventory.expire_reservations": {"queue": "inventory.maintenance"},
    "flashmarket.drops.run_scheduler_tick": {"queue": "drops.maintenance"},
    "flashmarket.media.cleanup_expired_assets": {"queue": "media.maintenance"},
}


def broker_url() -> str:
    """Return the isolated command-job broker URL."""
    return os.getenv(
        "CELERY_BROKER_URL",
        "amqp://shide:shide@shide-rabbitmq:5672/flashmarket-tasks",
    )


def create_app(
    name: str,
    *,
    include: Iterable[str] = (),
    beat_schedule: Mapping[str, Mapping[str, Any]] | None = None,
) -> Celery:
    """Create a consistently configured Celery app."""
    app = Celery(name, broker=broker_url(), include=list(include))
    app.conf.update(
        accept_content=["json"],
        beat_schedule=dict(beat_schedule or {}),
        beat_schedule_filename=os.getenv(
            "CELERY_BEAT_SCHEDULE_FILENAME", "/tmp/celerybeat-schedule"
        ),
        broker_connection_retry_on_startup=True,
        enable_utc=True,
        result_backend=None,
        task_acks_late=True,
        task_create_missing_queues=False,
        task_default_exchange="flashmarket.tasks",
        task_default_exchange_type="direct",
        task_default_queue="auth.maintenance",
        task_ignore_result=True,
        task_queues=tuple(
            Queue(queue, exchange="flashmarket.tasks", routing_key=queue, durable=True)
            for queue in QUEUES
        ),
        task_reject_on_worker_lost=True,
        task_routes=TASK_ROUTES,
        task_serializer="json",
        timezone="UTC",
        worker_prefetch_multiplier=1,
    )
    return app
