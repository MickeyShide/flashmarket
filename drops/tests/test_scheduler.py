"""Tests for drops background scheduler logic."""

from datetime import UTC, datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import pytest

from drops.domain.entities import DropEventType, DropStatus
from drops.infrastructure.models import DropModel, OutboxEventModel
from drops.scheduler import run_scheduler_tick


@pytest.mark.asyncio
async def test_scheduler_starts_and_ends_drops(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    now = datetime.now(UTC)

    # 1. Create a SCHEDULED drop with starts_at in the past
    async with session_factory() as session, session.begin():
        due_to_start_drop = DropModel(
            name="Due Start Drop",
            slug="due-start-drop",
            status=DropStatus.SCHEDULED,
            starts_at=now - timedelta(minutes=10),
            ends_at=now + timedelta(hours=2),
        )
        session.add(due_to_start_drop)

    # 2. Create an ACTIVE drop with ends_at in the past
    async with session_factory() as session, session.begin():
        due_to_end_drop = DropModel(
            name="Due End Drop",
            slug="due-end-drop",
            status=DropStatus.ACTIVE,
            starts_at=now - timedelta(hours=5),
            ends_at=now - timedelta(minutes=10),
        )
        session.add(due_to_end_drop)

    # Run scheduler tick
    await run_scheduler_tick()

    # Verify states and outbox events
    async with session_factory() as session:
        # Check start drop
        started = (
            await session.execute(
                select(DropModel).where(DropModel.slug == "due-start-drop")
            )
        ).scalar_one()
        assert started.status == DropStatus.ACTIVE

        # Check end drop
        ended = (
            await session.execute(
                select(DropModel).where(DropModel.slug == "due-end-drop")
            )
        ).scalar_one()
        assert ended.status == DropStatus.ENDED

        # Check outbox events emitted
        events = (await session.execute(select(OutboxEventModel))).scalars().all()
        event_types = [e.event_type for e in events]
        assert DropEventType.DROP_STARTED in event_types
        assert DropEventType.DROP_ENDED in event_types
