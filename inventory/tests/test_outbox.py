"""Unit tests for the transactional outbox relay."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from aio_pika.abc import AbstractExchange
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from inventory.infrastructure.models import OutboxEventModel
from inventory.outbox_worker import publish_outbox_batch


class CapturingExchange:
    """In-memory exchange that records published messages."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.published: list[tuple[object, str, bool]] = []

    async def publish(
        self,
        message: object,
        routing_key: str,
        *,
        mandatory: bool = False,
        immediate: bool = False,
        _timeout: float | None = None,
    ) -> Any:
        if self.error is not None:
            raise self.error
        self.published.append((message, routing_key, mandatory))
        return None


async def _add_event(
    session_factory: async_sessionmaker[AsyncSession],
) -> uuid.UUID:
    event_id = uuid.uuid7()
    async with session_factory() as db:
        db.add(
            OutboxEventModel(
                id=event_id,
                event_type="InventoryReserved",
                payload=json.dumps({"product_id": str(uuid.uuid7())}),
                created_at=datetime.now(UTC),
            )
        )
        await db.commit()
    return event_id


async def test_outbox_publisher_marks_confirmed_event_as_published(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    event_id = await _add_event(session_factory)
    exchange: AbstractExchange = CapturingExchange()  # type: ignore[assignment]

    processed = await publish_outbox_batch(exchange, session_factory=session_factory)

    assert processed == 1
    assert len(exchange.published) == 1  # type: ignore[attr-defined]
    _message, routing_key, mandatory = exchange.published[0]  # type: ignore[attr-defined]
    assert routing_key == "inventory.InventoryReserved"
    assert mandatory is False

    async with session_factory() as db:
        event = await db.get(OutboxEventModel, event_id)
        assert event is not None
        assert event.status == "published"
        assert event.published_at is not None
        assert event.attempts == 1


async def test_outbox_publisher_schedules_retry_after_failure(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    event_id = await _add_event(session_factory)
    exchange: AbstractExchange = CapturingExchange(RuntimeError("broker unavailable"))  # type: ignore[assignment]

    processed = await publish_outbox_batch(exchange, session_factory=session_factory)

    assert processed == 1
    assert len(exchange.published) == 0  # type: ignore[attr-defined]

    async with session_factory() as db:
        event = await db.scalar(select(OutboxEventModel).where(OutboxEventModel.id == event_id))
        assert event is not None
        assert event.status == "failed"
        assert event.published_at is None
        assert event.attempts == 1
