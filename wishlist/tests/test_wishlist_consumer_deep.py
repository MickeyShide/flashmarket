"""Deep consumer, deduplication, and malformed message tests for wishlist service."""

import json
import uuid
from unittest.mock import MagicMock

import pytest
from aio_pika.abc import AbstractIncomingMessage
from rabbitmq_reliability import PermanentMessageError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from wishlist.event_consumer import process_drop_started
from wishlist.infrastructure.models import OutboxEventModel, WishlistItemModel


@pytest.mark.asyncio
async def test_process_drop_started_stages_notifications_and_deduplicates(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """DropStarted event creates staged drop notifications and deduplicates on re-delivery."""
    user_1 = uuid.uuid4()
    user_2 = uuid.uuid4()
    user_3 = uuid.uuid4()
    prod_watched = uuid.uuid4()
    prod_other = uuid.uuid4()
    drop_id = uuid.uuid4()

    # Step 1: Prepopulate wishlist items
    async with session_factory() as session, session.begin():
        session.add(WishlistItemModel(user_id=user_1, product_id=prod_watched))
        session.add(WishlistItemModel(user_id=user_2, product_id=prod_watched))
        session.add(WishlistItemModel(user_id=user_3, product_id=prod_other))

    # Step 2: Construct DropStarted message for prod_watched
    payload = {
        "drop_id": str(drop_id),
        "product_ids": [str(prod_watched)],
        "name": "Exclusive Flash Drop",
        "slug": "exclusive-flash-drop",
    }
    mock_message = MagicMock(spec=AbstractIncomingMessage)
    mock_message.body = json.dumps(payload).encode("utf-8")
    mock_message.message_id = "drop-event-unique-uuid-1"
    mock_message.headers = {}

    # Delivery 1: Stages notifications for user_1 and user_2
    await process_drop_started(mock_message, session_factory=session_factory)

    async with session_factory() as session:
        events = (await session.scalars(select(OutboxEventModel))).all()
        assert len(events) == 2
        user_ids = {json.loads(e.payload)["user_id"] for e in events}
        assert user_ids == {str(user_1), str(user_2)}

    # Delivery 2 (Duplicate re-delivery with identical message_id): Should be skipped
    await process_drop_started(mock_message, session_factory=session_factory)

    async with session_factory() as session:
        events_after = (await session.scalars(select(OutboxEventModel))).all()
        assert len(events_after) == 2  # No duplicate staged events


@pytest.mark.asyncio
async def test_process_drop_started_malformed_payload_raises_permanent_error() -> None:
    """Malformed DropStarted payload missing required fields raises PermanentMessageError."""
    # Payload missing drop_id
    mock_message = MagicMock(spec=AbstractIncomingMessage)
    mock_message.body = json.dumps({"product_ids": [str(uuid.uuid4())]}).encode("utf-8")
    mock_message.message_id = "malformed-drop-event-1"
    mock_message.headers = {}

    with pytest.raises(PermanentMessageError, match="invalid DropStarted payload"):
        await process_drop_started(mock_message)
