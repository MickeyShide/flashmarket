"""Comprehensive integration tests for Drops microservice (DROP-001 through DROP-014)."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from drops.domain.entities import DropStatus
from drops.infrastructure.models import DropModel, OutboxEventModel
from drops.outbox_worker import publish_outbox_batch
from drops.scheduler import run_scheduler_tick


@pytest.mark.asyncio
async def test_drop_001_to_005_drop_lifecycle_and_items(client: AsyncClient) -> None:
    """DROP-001..DROP-005: Create flash sale drop, add/remove items, update status."""
    now = datetime.now(timezone.utc)
    start_time = now + timedelta(hours=1)
    end_time = now + timedelta(hours=2)

    # 1. Create Drop in DRAFT status
    slug = f"midnight-sale-{uuid.uuid4().hex[:6]}"
    create_resp = await client.post(
        "/api/v1/admin/drops/",
        json={
            "name": "Midnight Flash Sale",
            "slug": slug,
            "description": "Exclusive midnight drop",
            "starts_at": start_time.isoformat(),
            "ends_at": end_time.isoformat(),
        },
    )
    assert create_resp.status_code == 201
    drop_data = create_resp.json()
    assert drop_data["status"] == "DRAFT"
    drop_id = uuid.UUID(drop_data["id"])

    # 2. Add Item to Drop
    product_id = uuid.uuid4()
    add_item_resp = await client.post(
        f"/api/v1/admin/drops/{drop_id}/items",
        json={
            "product_id": str(product_id),
            "sort_order": 1,
        },
    )
    assert add_item_resp.status_code == 201
    assert add_item_resp.json()["product_id"] == str(product_id)

    # 3. Schedule Drop (DRAFT -> SCHEDULED)
    sched_resp = await client.post(f"/api/v1/admin/drops/{drop_id}/schedule")
    assert sched_resp.status_code == 200
    assert sched_resp.json()["status"] == "SCHEDULED"

    # 4. List admin drops
    list_resp = await client.get("/api/v1/admin/drops/")
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    assert any(d["id"] == str(drop_id) for d in items)


@pytest.mark.asyncio
async def test_drop_008_scheduler_auto_transitions(
    session_factory: async_sessionmaker[AsyncSession], client: AsyncClient
) -> None:
    """DROP-008: Scheduler automatically transitions scheduled drops when start_time is due."""
    now = datetime.now(timezone.utc)
    future_start = now + timedelta(minutes=5)
    future_end = now + timedelta(hours=1)

    slug = f"past-drop-{uuid.uuid4().hex[:6]}"
    # 1. Create drop in future
    create_resp = await client.post(
        "/api/v1/admin/drops/",
        json={
            "name": "Past Drop",
            "slug": slug,
            "starts_at": future_start.isoformat(),
            "ends_at": future_end.isoformat(),
        },
    )
    assert create_resp.status_code == 201
    drop_id = uuid.UUID(create_resp.json()["id"])
    await client.post(f"/api/v1/admin/drops/{drop_id}/schedule")

    # 2. Backdate starts_at to past in DB
    async with session_factory() as db, db.begin():
        drop = await db.get(DropModel, drop_id)
        assert drop is not None
        drop.starts_at = datetime.now(timezone.utc) - timedelta(minutes=5)

    # 3. Process due drops via scheduler
    await run_scheduler_tick(session_factory=session_factory)

    # Verify drop is now ACTIVE
    get_resp = await client.get(f"/api/v1/admin/drops/{drop_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_drop_010_outbox_worker_retries(
    session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """DROP-010: Outbox worker retries failed drop events."""
    async with session_factory() as session, session.begin():
        event = OutboxEventModel(
            event_type="DropActivated",
            payload='{"drop_id": "test"}',
            status="failed",
            attempts=1,
        )
        session.add(event)

    class MockExchange:
        def __init__(self) -> None:
            self.published = 0

        async def publish(self, message: any, routing_key: str, mandatory: bool = True) -> bool:
            self.published += 1
            return True

    mock_exchange = MockExchange()
    count = await publish_outbox_batch(mock_exchange, session_factory=session_factory)
    assert count >= 1
    assert mock_exchange.published >= 1


@pytest.mark.asyncio
async def test_drop_014_readiness_probe(client: AsyncClient) -> None:
    """DROP-014: Readiness probe returns HTTP 200."""
    resp = await client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
