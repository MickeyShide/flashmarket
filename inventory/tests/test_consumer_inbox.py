"""Consumer redeliveries are idempotent inside the business transaction."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from inventory.event_consumer import HANDLERS, process_message
from inventory.infrastructure.models import ProcessedEventModel


@pytest.mark.asyncio
async def test_duplicate_delivery_runs_handler_once(
    session_factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    handler = AsyncMock(return_value=None)
    monkeypatch.setitem(HANDLERS, "test.Event", handler)
    message = SimpleNamespace(
        body=b'{"value":1}',
        headers={},
        routing_key="test.Event",
        message_id="same-event-id",
    )

    await process_message(message, session_factory=session_factory)
    await process_message(message, session_factory=session_factory)

    handler.assert_awaited_once()
    async with session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(ProcessedEventModel)) == 1
