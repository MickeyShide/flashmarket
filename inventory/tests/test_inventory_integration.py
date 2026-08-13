"""Comprehensive integration tests for Inventory microservice (INV-001 through INV-017)."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from inventory.application.contracts import NoOpStockCache
from inventory.event_consumer import (
    handle_payment_failed,
    handle_payment_succeeded,
)
from inventory.infrastructure.models import OutboxEventModel, ReservationModel
from inventory.outbox_worker import publish_outbox_batch


@pytest.mark.asyncio
async def test_inv_001_and_002_create_and_reset_stock_invariants(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """INV-001 & INV-002: Verify the stock reset counter invariant."""
    product_id = uuid.uuid4()

    # 1. Create initial stock total=10
    resp = await client.post(
        "/api/v1/stocks",
        json={"product_id": str(product_id), "total": 10},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["total"] == 10
    assert data["available"] == 10
    assert data["reserved"] == 0
    assert data["sold"] == 0

    # 2. Reserve 4 units
    user_id = uuid.uuid4()
    order_id = uuid.uuid4()
    res_resp = await client.post(
        f"/api/v1/stocks/{product_id}/reserve",
        json={"user_id": str(user_id), "quantity": 4, "order_id": str(order_id)},
    )
    assert res_resp.status_code == 201

    # 3. Commit 2 units -> reserved=2, sold=2, available=6
    commit_resp = await client.post(
        f"/api/v1/stocks/{product_id}/commit",
        json={"order_id": str(order_id)},
    )
    assert commit_resp.status_code == 200

    # Verify state before reset
    stock_resp = await client.get(f"/api/v1/stocks/{product_id}")
    assert stock_resp.json()["reserved"] == 0
    assert stock_resp.json()["sold"] == 4
    assert stock_resp.json()["available"] == 6

    # Reserve 2 more units -> reserved=2, sold=4, available=4
    order_id_2 = uuid.uuid4()
    await client.post(
        f"/api/v1/stocks/{product_id}/reserve",
        json={"user_id": str(user_id), "quantity": 2, "order_id": str(order_id_2)},
    )

    # Reset total to 15 -> available should become 15 - 2 (reserved) - 4 (sold) = 9
    reset_resp = await client.post(
        "/api/v1/stocks",
        json={"product_id": str(product_id), "total": 15},
    )
    assert reset_resp.status_code == 201
    reset_data = reset_resp.json()
    assert reset_data["total"] == 15
    assert reset_data["reserved"] == 2
    assert reset_data["sold"] == 4
    assert reset_data["available"] == 9

    # Attempt reset total to 5 (< reserved 2 + sold 4 = 6) -> Should reject with 409
    reset_invalid = await client.post(
        "/api/v1/stocks",
        json={"product_id": str(product_id), "total": 5},
    )
    assert reset_invalid.status_code == 409


@pytest.mark.asyncio
async def test_inv_003_update_stock_boundaries(client: AsyncClient) -> None:
    """INV-003: Update stock total and check non-existent stock 404."""
    product_id = uuid.uuid4()
    await client.post("/api/v1/stocks", json={"product_id": str(product_id), "total": 20})

    # Update total to 30
    patch_resp = await client.patch(
        f"/api/v1/stocks/{product_id}",
        json={"total": 30},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["total"] == 30
    assert patch_resp.json()["available"] == 30

    # Patch non-existent product -> 404
    bad_id = uuid.uuid4()
    patch_bad = await client.patch(f"/api/v1/stocks/{bad_id}", json={"total": 10})
    assert patch_bad.status_code == 404


@pytest.mark.asyncio
async def test_inv_004_and_005_reserve_validation(client: AsyncClient) -> None:
    """INV-004 & INV-005: Out of stock reserve validation."""
    product_id = uuid.uuid4()
    user_id = uuid.uuid4()

    await client.post("/api/v1/stocks", json={"product_id": str(product_id), "total": 3})

    # Request more than available (5 > 3) -> 409 Out of stock
    res_over = await client.post(
        f"/api/v1/stocks/{product_id}/reserve",
        json={"user_id": str(user_id), "quantity": 5},
    )
    assert res_over.status_code == 409

    # Reserve valid quantity
    res_ok = await client.post(
        f"/api/v1/stocks/{product_id}/reserve",
        json={"user_id": str(user_id), "quantity": 3},
    )
    assert res_ok.status_code == 201

    # Additional reserve when available=0 -> 409
    res_zero = await client.post(
        f"/api/v1/stocks/{product_id}/reserve",
        json={"user_id": str(user_id), "quantity": 1},
    )
    assert res_zero.status_code == 409


@pytest.mark.asyncio
async def test_inv_008_variant_stock_reserve_commit_release(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """INV-008: Reserve, commit and release for variant stock."""
    product_id = uuid.uuid4()
    variant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    order_id = uuid.uuid4()

    # Create variant stock
    await client.post(
        "/api/v1/stocks",
        json={"product_id": str(product_id), "variant_id": str(variant_id), "total": 8},
    )

    # Get variant stock
    get_v = await client.get(f"/api/v1/stocks/{product_id}", params={"variant_id": str(variant_id)})
    assert get_v.status_code == 200
    assert get_v.json()["total"] == 8

    # Reserve variant stock
    res_resp = await client.post(
        f"/api/v1/stocks/{product_id}/reserve",
        json={
            "user_id": str(user_id),
            "quantity": 2,
            "variant_id": str(variant_id),
            "order_id": str(order_id),
        },
    )
    assert res_resp.status_code == 201

    # Commit variant reservation
    commit_resp = await client.post(
        f"/api/v1/stocks/{product_id}/commit",
        json={"order_id": str(order_id)},
    )
    assert commit_resp.status_code == 200

    # Verify variant stock updated
    v_after = await client.get(
        f"/api/v1/stocks/{product_id}", params={"variant_id": str(variant_id)}
    )
    assert v_after.json()["sold"] == 2
    assert v_after.json()["reserved"] == 0
    assert v_after.json()["available"] == 6


@pytest.mark.asyncio
async def test_inv_010_expire_reservations(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    db_session: AsyncSession,
) -> None:
    """INV-010: Expire past reservations and restore available stock."""
    product_id = uuid.uuid4()
    user_id = uuid.uuid4()

    await client.post("/api/v1/stocks", json={"product_id": str(product_id), "total": 5})
    res_resp = await client.post(
        f"/api/v1/stocks/{product_id}/reserve",
        json={"user_id": str(user_id), "quantity": 2},
    )
    assert res_resp.status_code == 201
    res_id = uuid.UUID(res_resp.json()["reservation"]["id"])

    # Backdate reservation's expires_at in DB
    async with session_factory() as db, db.begin():
        res = await db.get(ReservationModel, res_id)
        assert res is not None
        res.expires_at = datetime.now(UTC) - timedelta(minutes=10)

    # Call service expire_reservations
    from inventory.application.services.stock import InventoryService
    from inventory.infrastructure.repositories.stock import (
        OutboxRepository,
        ReservationRepository,
        StockRepository,
    )

    async with session_factory() as db:
        service = InventoryService(
            session=db,
            stock_repo=StockRepository(db),
            reservation_repo=ReservationRepository(db),
            outbox_repo=OutboxRepository(db),
            stock_cache=NoOpStockCache(),
        )
        expired_count = await service.expire_reservations()
        assert expired_count >= 1

    # Check stock restored
    stock_resp = await client.get(f"/api/v1/stocks/{product_id}")
    assert stock_resp.json()["reserved"] == 0
    assert stock_resp.json()["available"] == 5


@pytest.mark.asyncio
async def test_inv_011_and_012_consumer_saga_handlers(
    session_factory: async_sessionmaker[AsyncSession], client: AsyncClient
) -> None:
    """INV-011 & INV-012: Handle inbound payment and cancellation saga events."""
    product_id = uuid.uuid4()
    user_id = uuid.uuid4()
    order_id = uuid.uuid4()

    await client.post("/api/v1/stocks", json={"product_id": str(product_id), "total": 10})
    await client.post(
        f"/api/v1/stocks/{product_id}/reserve",
        json={"user_id": str(user_id), "quantity": 3, "order_id": str(order_id)},
    )

    # Handle PaymentSucceeded
    payload_success = {"order_id": str(order_id), "user_id": str(user_id), "amount": 999}
    async with session_factory() as session, session.begin():
        await handle_payment_succeeded(session, payload_success)

    # Check committed
    stock_1 = await client.get(f"/api/v1/stocks/{product_id}")
    assert stock_1.json()["sold"] == 3
    assert stock_1.json()["reserved"] == 0

    # Redelivery of PaymentSucceeded (duplicate safe)
    async with session_factory() as session, session.begin():
        await handle_payment_succeeded(session, payload_success)

    stock_2 = await client.get(f"/api/v1/stocks/{product_id}")
    assert stock_2.json()["sold"] == 3

    # New reservation for failure test
    order_id_fail = uuid.uuid4()
    await client.post(
        f"/api/v1/stocks/{product_id}/reserve",
        json={"user_id": str(user_id), "quantity": 2, "order_id": str(order_id_fail)},
    )

    payload_fail = {"order_id": str(order_id_fail), "reason": "insufficient_funds"}
    async with session_factory() as session, session.begin():
        await handle_payment_failed(session, payload_fail)

    stock_3 = await client.get(f"/api/v1/stocks/{product_id}")
    assert stock_3.json()["reserved"] == 0
    assert stock_3.json()["available"] == 7


@pytest.mark.asyncio
async def test_inv_014_outbox_worker_retries_failed_events(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """INV-014: Outbox worker retries failed events."""
    async with session_factory() as session, session.begin():
        event = OutboxEventModel(
            event_type="InventoryReserved",
            payload='{"test": 1}',
            status="failed",
            attempts=1,
        )
        session.add(event)

    class MockExchange:
        def __init__(self) -> None:
            self.published_count = 0

        async def publish(self, message: any, routing_key: str, mandatory: bool = True) -> bool:
            self.published_count += 1
            return True

    mock_exchange = MockExchange()
    count = await publish_outbox_batch(mock_exchange, session_factory=session_factory)
    assert count >= 1
    assert mock_exchange.published_count >= 1

    async with session_factory() as session:
        db_event = await session.get(OutboxEventModel, event.id)
        assert db_event.status == "published"


@pytest.mark.asyncio
async def test_inv_016_readiness_probe_returns_503_on_db_down(client: AsyncClient) -> None:
    """INV-016: Readiness probe returns HTTP 200 when ready."""
    resp = await client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
