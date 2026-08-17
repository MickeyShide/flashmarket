"""Media maintenance tasks."""

import logging

from celery import signals  # type: ignore[import-untyped]
from flashmarket_celery import AsyncRunner
from rabbitmq_reliability import ensure_worker_metrics_server, touch_heartbeat

from media_service.api.dependencies import get_storage
from media_service.application.services.cleanup import CleanupService
from media_service.celery_app import app
from media_service.config import get_settings
from media_service.infrastructure.database import SessionFactory, engine
from media_service.infrastructure.repositories import MediaAssetRepository
from media_service.observability import CLEANUP_FAILURES

logger = logging.getLogger(__name__)
runner = AsyncRunner()


async def cleanup_expired_assets_once() -> int:
    """Process one bounded batch of expired or deleted assets."""
    settings = get_settings()
    try:
        async with SessionFactory() as session:
            processed = await CleanupService(
                session,
                MediaAssetRepository(session),
                get_storage(),
            ).run_once(settings.cleanup_batch_size)
    except Exception:
        CLEANUP_FAILURES.inc()
        raise

    if processed:
        logger.info("Media cleanup batch completed", extra={"processed": processed})
    touch_heartbeat("/tmp/flashmarket-heartbeat.json", "media_cleanup")
    return processed


@app.task(  # type: ignore[untyped-decorator]
    name="flashmarket.media.cleanup_expired_assets",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
    acks_late=True,
)
def cleanup_expired_assets_task() -> int:
    """Celery entry point for Media cleanup."""
    return runner.run(cleanup_expired_assets_once())


@signals.worker_process_init.connect  # type: ignore[untyped-decorator]
def initialize_worker_process(**_: object) -> None:
    """Expose worker progress metrics before the first scheduled task."""
    ensure_worker_metrics_server()


@signals.worker_process_shutdown.connect  # type: ignore[untyped-decorator]
def shutdown_worker_process(**_: object) -> None:
    """Dispose the child-owned async SQLAlchemy pool."""
    runner.shutdown(engine.dispose())
