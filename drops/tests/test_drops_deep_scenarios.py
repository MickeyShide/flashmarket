import json
import uuid
from unittest.mock import AsyncMock

import pytest
from aio_pika.abc import AbstractExchange
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from drops.domain.entities import DropEventType
from drops.infrastructure.models import OutboxEventModel
from drops.outbox_worker import publish_outbox_batch


@pytest.mark.asyncio
async def test_publish_outbox_batch_records_failure_and_retries(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Outbox worker records retry attempts on broker failure and recovers."""
    event_id = uuid.uuid7()
    drop_id = uuid.uuid7()
    payload = {
        "drop_id": str(drop_id),
        "name": "Resilient Drop",
        "slug": "resilient-drop",
    }

    # Step 1: Prepopulate pending outbox event
    async with session_factory() as session, session.begin():
        session.add(
            OutboxEventModel(
                id=event_id,
                event_type=DropEventType.DROP_STARTED,
                payload=json.dumps(payload),
                status="pending",
                attempts=0,
            )
        )

    # Step 2: Simulate RabbitMQ broker connection failure
    failing_exchange = AsyncMock(spec=AbstractExchange)
    failing_exchange.publish.side_effect = RuntimeError("RabbitMQ connection lost")

    processed_fail = await publish_outbox_batch(
        failing_exchange,
        session_factory=session_factory,
    )
    assert processed_fail == 1

    # Verify event recorded failure attempt
    async with session_factory() as session:
        event = await session.get(OutboxEventModel, event_id)
        assert event is not None
        assert event.status == "failed"
        assert event.attempts == 1
        assert "RabbitMQ connection lost" in str(event.last_error)

    # Step 3: Simulate recovery: healthy broker exchange
    healthy_exchange = AsyncMock(spec=AbstractExchange)

    # Note: Event with status 'failed' can be claimed if due
    # Let's reset next_attempt_at to None so it can be claimed immediately
    async with session_factory() as session, session.begin():
        evt = await session.get(OutboxEventModel, event_id)
        assert evt is not None
        evt.next_attempt_at = None

    processed_success = await publish_outbox_batch(
        healthy_exchange,
        session_factory=session_factory,
    )
    assert processed_success == 1
    assert healthy_exchange.publish.call_count == 1

    # Verify event is now marked published
    async with session_factory() as session:
        event = await session.get(OutboxEventModel, event_id)
        assert event is not None
        assert event.status == "published"
        assert event.published_at is not None
