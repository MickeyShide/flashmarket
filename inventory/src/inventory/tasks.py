"""Inventory maintenance tasks."""

import logging

from celery import signals  # type: ignore[import-untyped]
from flashmarket_celery import AsyncRunner
from rabbitmq_reliability import ensure_worker_metrics_server, touch_heartbeat

from inventory.application.services.stock import InventoryService
from inventory.celery_app import app
from inventory.infrastructure.database import SessionFactory, engine
from inventory.infrastructure.repositories.stock import (
    OutboxRepository,
    ReservationRepository,
    StockRepository,
)
from inventory.infrastructure.stock_cache import redis_client, stock_cache

logger = logging.getLogger(__name__)
runner = AsyncRunner()


async def expire_reservations_once() -> int:
    """Release one batch of expired reservations."""
    async with SessionFactory() as session:
        service = InventoryService(
            session=session,
            stock_repo=StockRepository(session),
            reservation_repo=ReservationRepository(session),
            outbox_repo=OutboxRepository(session),
            stock_cache=stock_cache,
        )
        expired = await service.expire_reservations()
    if expired:
        logger.info("Expired %s reservation(s)", expired)
    touch_heartbeat("/tmp/flashmarket-heartbeat.json", "inventory_expiry")
    return expired


@app.task(  # type: ignore[untyped-decorator]
    name="flashmarket.inventory.expire_reservations",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
    acks_late=True,
)
def expire_reservations_task() -> int:
    """Celery entry point for reservation expiry."""
    return runner.run(expire_reservations_once())


@signals.worker_process_init.connect  # type: ignore[untyped-decorator]
def initialize_worker_process(**_: object) -> None:
    """Expose worker progress metrics before the first scheduled task."""
    ensure_worker_metrics_server()


async def _close_resources() -> None:
    await redis_client.aclose()
    await engine.dispose()


@signals.worker_process_shutdown.connect  # type: ignore[untyped-decorator]
def shutdown_worker_process(**_: object) -> None:
    """Dispose child-owned async clients before the loop exits."""
    runner.shutdown(_close_resources())
