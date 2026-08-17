"""One-shot scheduler operation for starting and ending flash-sale drops."""

import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from drops.domain.entities import DropEventType, DropStatus
from drops.infrastructure.database import SessionFactory, utc_now
from drops.infrastructure.models import OutboxEventModel
from drops.infrastructure.repositories.drop import DropRepository

logger = logging.getLogger("drops.scheduler")


async def run_scheduler_tick(
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> None:
    """Perform one iteration of drop state checks."""
    factory = session_factory or SessionFactory
    now = utc_now()
    async with factory() as session, session.begin():
        repo = DropRepository(session)

        # 1. Start due SCHEDULED drops
        due_to_start = await repo.get_due_to_start(now)
        for drop in due_to_start:
            drop.status = DropStatus.ACTIVE
            event = OutboxEventModel(
                event_type=DropEventType.DROP_STARTED,
                payload=json.dumps(
                    {
                        "drop_id": str(drop.id),
                        "name": drop.name,
                        "slug": drop.slug,
                        "product_ids": [str(item.product_id) for item in drop.items],
                        "max_per_user": drop.max_per_user,
                    }
                ),
                status="pending",
            )
            session.add(event)
            logger.info("Drop %s (%s) automatically started", drop.id, drop.slug)

        # 2. End due ACTIVE drops
        due_to_end = await repo.get_due_to_end(now)
        for drop in due_to_end:
            drop.status = DropStatus.ENDED
            event = OutboxEventModel(
                event_type=DropEventType.DROP_ENDED,
                payload=json.dumps(
                    {
                        "drop_id": str(drop.id),
                        "slug": drop.slug,
                    }
                ),
                status="pending",
            )
            session.add(event)
            logger.info("Drop %s (%s) automatically ended", drop.id, drop.slug)
