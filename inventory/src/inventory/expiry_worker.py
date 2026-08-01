"""Periodic release of expired stock reservations."""

import asyncio
import logging

from inventory.application.services.stock import InventoryService
from inventory.config import get_settings
from inventory.infrastructure.database import SessionFactory, engine
from inventory.infrastructure.repositories.stock import (
    OutboxRepository,
    ReservationRepository,
    StockRepository,
)
from inventory.infrastructure.stock_cache import redis_client, stock_cache

logger = logging.getLogger(__name__)


async def run() -> None:
    settings = get_settings()
    try:
        while True:
            try:
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
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Reservation expiry tick failed")
            await asyncio.sleep(settings.expiry_poll_interval_seconds)
    finally:
        await redis_client.aclose()
        await engine.dispose()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())


if __name__ == "__main__":
    main()
