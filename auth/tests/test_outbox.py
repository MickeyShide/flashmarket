import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from auth_service.models import OutboxEvent
from auth_service.outbox_worker import publish_outbox_batch


class CapturingExchange:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.published: list[tuple[object, str, bool]] = []

    async def publish(
        self,
        message: object,
        routing_key: str,
        *,
        mandatory: bool,
    ) -> None:
        if self.error is not None:
            raise self.error
        self.published.append((message, routing_key, mandatory))


async def _add_event(
    session_factory: async_sessionmaker[AsyncSession],
) -> uuid.UUID:
    event_id = uuid.uuid7()
    async with session_factory() as db:
        db.add(
            OutboxEvent(
                id=event_id,
                event_type="user_registered",
                aggregate_type="user",
                aggregate_id=uuid.uuid7(),
                payload={"schema_version": 1, "event_id": str(event_id)},
                occurred_at=datetime.now(UTC),
            )
        )
        await db.commit()
    return event_id


async def test_outbox_publisher_marks_confirmed_event_as_published(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    event_id = await _add_event(session_factory)
    exchange = CapturingExchange()

    processed = await publish_outbox_batch(  # type: ignore[arg-type]
        exchange,
        session_factory=session_factory,
    )

    assert processed == 1
    assert len(exchange.published) == 1
    message, routing_key, mandatory = exchange.published[0]
    assert routing_key == "identity.user_registered"
    assert mandatory is True
    assert json.loads(message.body) == {
        "schema_version": 1,
        "event_id": str(event_id),
    }
    async with session_factory() as db:
        event = await db.get(OutboxEvent, event_id)
        assert event is not None
        assert event.published_at is not None
        assert event.attempts == 1
        assert event.last_error is None


async def test_outbox_publisher_schedules_retry_after_failure(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    event_id = await _add_event(session_factory)
    exchange = CapturingExchange(RuntimeError("broker unavailable"))

    processed = await publish_outbox_batch(  # type: ignore[arg-type]
        exchange,
        session_factory=session_factory,
    )

    assert processed == 1
    async with session_factory() as db:
        event = await db.scalar(select(OutboxEvent).where(OutboxEvent.id == event_id))
        assert event is not None
        assert event.published_at is None
        assert event.attempts == 1
        assert event.next_attempt_at is not None
        assert event.last_error == "broker unavailable"
