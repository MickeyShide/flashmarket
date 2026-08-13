"""Tests for drops background scheduler logic."""

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from drops.domain.entities import DropEventType, DropStatus
from drops.infrastructure.models import DropModel, OutboxEventModel
from drops.scheduler import main, run_scheduler_tick


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
async def test_scheduler_heartbeat_is_independent_of_tick_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    heartbeat_calls: list[tuple[str, int, str]] = []

    @asynccontextmanager
    async def fake_periodic_heartbeat(path: str, *, interval_seconds: int, phase: str):
        heartbeat_calls.append((path, interval_seconds, phase))
        yield

    failing_tick = AsyncMock(side_effect=RuntimeError("database unavailable"))
    stop_loop = AsyncMock(side_effect=asyncio.CancelledError)
    monkeypatch.setattr("drops.scheduler.periodic_heartbeat", fake_periodic_heartbeat)
    monkeypatch.setattr("drops.scheduler.run_scheduler_tick", failing_tick)
    monkeypatch.setattr("drops.scheduler.asyncio.sleep", stop_loop)
    monkeypatch.setattr("drops.scheduler.setup_metrics", lambda: None)

    with pytest.raises(asyncio.CancelledError):
        await main()

    assert heartbeat_calls == [("/tmp/flashmarket-heartbeat.json", 10, "drops_scheduler")]
    failing_tick.assert_awaited_once()
