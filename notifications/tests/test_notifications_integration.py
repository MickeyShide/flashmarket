"""Comprehensive integration tests for Notifications microservice (NOT-001 through NOT-012)."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from notifications.event_consumer import (
    handle_order_cancelled,
    handle_order_confirmed,
    handle_order_created,
)
from notifications.infrastructure.models import NotificationModel, OutboxEventModel
from notifications.outbox_worker import publish_outbox_batch


@pytest.mark.asyncio
async def test_not_001_to_005_consumer_handlers_and_deduplication(
    session_factory: async_sessionmaker[AsyncSession], client: AsyncClient
) -> None:
    """NOT-001..NOT-005: Event consumer handlers for OrderCreated, OrderConfirmed, OrderCancelled and deduplication."""
    user_id = uuid.uuid4()
    order_id = uuid.uuid4()

    created_payload = {
        "order_id": str(order_id),
        "user_id": str(user_id),
        "product_name": "Pro Keyboard",
        "amount": 12000,
    }

    # 1. Handle OrderCreated
    async with session_factory() as session, session.begin():
        await handle_order_created(session, created_payload)

    # Verify notification created
    list_1 = await client.get(f"/api/v1/notifications/users/{user_id}")
    assert list_1.status_code == 200
    items_1 = list_1.json()["items"]
    assert len(items_1) == 1
    assert items_1[0]["subject"] == "Order created"

    # 2. Redelivery of OrderCreated (Deduplication check)
    async with session_factory() as session, session.begin():
        await handle_order_created(session, created_payload)

    list_2 = await client.get(f"/api/v1/notifications/users/{user_id}")
    assert len(list_2.json()["items"]) == 1

    # 3. Handle OrderConfirmed
    confirmed_payload = {
        "order_id": str(order_id),
        "user_id": str(user_id),
        "payment_id": str(uuid.uuid4()),
    }
    async with session_factory() as session, session.begin():
        await handle_order_confirmed(session, confirmed_payload)

    list_3 = await client.get(f"/api/v1/notifications/users/{user_id}")
    items_3 = list_3.json()["items"]
    assert len(items_3) == 2
    assert any(n["subject"] == "Order confirmed" for n in items_3)

    # 4. Redelivery of OrderConfirmed
    async with session_factory() as session, session.begin():
        await handle_order_confirmed(session, confirmed_payload)

    list_4 = await client.get(f"/api/v1/notifications/users/{user_id}")
    assert len(list_4.json()["items"]) == 2

    # 5. Handle OrderCancelled for a second order
    order_id_2 = uuid.uuid4()
    cancelled_payload = {
        "order_id": str(order_id_2),
        "user_id": str(user_id),
        "reason": "Payment failed",
    }
    async with session_factory() as session, session.begin():
        await handle_order_cancelled(session, cancelled_payload)

    list_5 = await client.get(f"/api/v1/notifications/users/{user_id}")
    assert any(n["subject"] == "Order cancelled" for n in list_5.json()["items"])


@pytest.mark.asyncio
async def test_not_009_outbox_worker_retries(
    session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """NOT-009: Outbox worker retries failed notification events."""
    async with session_factory() as session, session.begin():
        event = OutboxEventModel(
            event_type="NotificationSent",
            payload='{"notification_id": "test"}',
            status="failed",
            attempts=1,
        )
        session.add(event)

    class MockExchange:
        def __init__(self) -> None:
            self.published = 0

        async def publish(self, message: any, routing_key: str, mandatory: bool = True) -> None:
            self.published += 1

    mock_exchange = MockExchange()
    count = await publish_outbox_batch(mock_exchange, session_factory=session_factory)
    assert count >= 1
    assert mock_exchange.published >= 1


@pytest.mark.asyncio
async def test_not_012_readiness_probe(client: AsyncClient) -> None:
    """NOT-012: Readiness probe returns HTTP 200."""
    resp = await client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
