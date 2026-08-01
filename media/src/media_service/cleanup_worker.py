"""Polling worker for expired uploads and requested deletions."""

import asyncio
import logging

from media_service.api.dependencies import get_storage
from media_service.application.services.cleanup import CleanupService
from media_service.config import get_settings
from media_service.infrastructure.database import SessionFactory, engine
from media_service.infrastructure.repositories import MediaAssetRepository
from media_service.observability import CLEANUP_FAILURES, setup_observability

logger = logging.getLogger(__name__)


async def run() -> None:
    settings = get_settings()
    setup_observability()
    storage = get_storage()
    try:
        while True:
            try:
                async with SessionFactory() as session:
                    processed = await CleanupService(
                        session, MediaAssetRepository(session), storage
                    ).run_once(settings.cleanup_batch_size)
                    if processed:
                        logger.info("media cleanup batch completed", extra={"processed": processed})
            except Exception:
                CLEANUP_FAILURES.inc()
                logger.exception("media cleanup batch failed")
            await asyncio.sleep(settings.cleanup_interval_seconds)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
