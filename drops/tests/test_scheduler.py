"""Tests for drops background scheduler logic."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from drops.domain.entities import DropEventType, DropStatus
from drops.infrastructure.models import DropModel, OutboxEventModel
from drops.infrastructure.repositories.drop import DropRepository
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
    await run_scheduler_tick(session_factory)

    # Verify states and outbox events
    async with session_factory() as session:
        # Check start drop
        started = (
            await session.execute(select(DropModel).where(DropModel.slug == "due-start-drop"))
        ).scalar_one()
        assert started.status == DropStatus.ACTIVE

        # Check end drop
        ended = (
            await session.execute(select(DropModel).where(DropModel.slug == "due-end-drop"))
        ).scalar_one()
        assert ended.status == DropStatus.ENDED

        # Check outbox events emitted
        events = (await session.execute(select(OutboxEventModel))).scalars().all()
        event_types = [e.event_type for e in events]
        assert DropEventType.DROP_STARTED in event_types
        assert DropEventType.DROP_ENDED in event_types


@pytest.mark.asyncio
@pytest.mark.parametrize("method_name", ["get_due_to_start", "get_due_to_end"])
async def test_scheduler_due_queries_skip_rows_locked_by_another_tick(method_name: str) -> None:
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    session.execute.return_value = result
    repo = DropRepository(session)

    await getattr(repo, method_name)(datetime.now(UTC))

    statement = session.execute.await_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert "FOR UPDATE SKIP LOCKED" in sql
