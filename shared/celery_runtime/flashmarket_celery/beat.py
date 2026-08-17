"""Singleton Beat schedule for FlashMarket maintenance commands."""

from __future__ import annotations

import os

from flashmarket_celery.app import create_app


def _seconds(name: str, default: float) -> float:
    raw = os.getenv(name)
    value = default if raw is None else float(raw)
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


app = create_app(
    "flashmarket-maintenance-beat",
    beat_schedule={
        "auth-cleanup-expired-data": {
            "task": "flashmarket.auth.cleanup_expired_data",
            "schedule": _seconds("CELERY_AUTH_CLEANUP_INTERVAL_SECONDS", 3600),
            "options": {"queue": "auth.maintenance"},
        },
        "inventory-expire-reservations": {
            "task": "flashmarket.inventory.expire_reservations",
            "schedule": _seconds("CELERY_INVENTORY_EXPIRY_INTERVAL_SECONDS", 5),
            "options": {"queue": "inventory.maintenance"},
        },
        "drops-run-scheduler-tick": {
            "task": "flashmarket.drops.run_scheduler_tick",
            "schedule": _seconds("CELERY_DROPS_SCHEDULER_INTERVAL_SECONDS", 10),
            "options": {"queue": "drops.maintenance"},
        },
        "media-cleanup-expired-assets": {
            "task": "flashmarket.media.cleanup_expired_assets",
            "schedule": _seconds("CELERY_MEDIA_CLEANUP_INTERVAL_SECONDS", 30),
            "options": {"queue": "media.maintenance"},
        },
    },
)
