"""Auth maintenance tasks."""

import logging

from celery import signals  # type: ignore[import-untyped]
from flashmarket_celery import AsyncRunner
from rabbitmq_reliability import ensure_worker_metrics_server, touch_heartbeat

from auth_service.celery_app import app
from auth_service.database import engine
from auth_service.maintenance import cleanup_expired_data

logger = logging.getLogger(__name__)
runner = AsyncRunner()


async def cleanup_expired_data_once() -> int:
    """Run one cleanup transaction and return the number of deleted rows."""
    counts = await cleanup_expired_data()
    total = counts.sessions + counts.refresh_tokens + counts.audit_events + counts.outbox_events
    logger.info(
        "Auth cleanup completed: sessions=%s refresh_tokens=%s audit_events=%s outbox_events=%s",
        counts.sessions,
        counts.refresh_tokens,
        counts.audit_events,
        counts.outbox_events,
    )
    touch_heartbeat("/tmp/flashmarket-heartbeat.json", "auth_cleanup")
    return total


@app.task(name="flashmarket.auth.cleanup_expired_data")  # type: ignore[untyped-decorator]
def cleanup_expired_data_task() -> int:
    """Celery entry point for Auth cleanup."""
    return runner.run(cleanup_expired_data_once())


@signals.worker_process_init.connect  # type: ignore[untyped-decorator]
def initialize_worker_process(**_: object) -> None:
    """Expose worker progress metrics before the first scheduled task."""
    ensure_worker_metrics_server()


@signals.worker_process_shutdown.connect  # type: ignore[untyped-decorator]
def shutdown_worker_process(**_: object) -> None:
    """Dispose the child-owned async SQLAlchemy pool."""
    runner.shutdown(engine.dispose())
