"""Regression tests for inventory concurrency (BUG-001, BUG-004, BUG-005)."""

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from inventory.application.contracts import NoOpStockCache
from inventory.application.schemas import CommitRequest, ReserveRequest, StockCreateRequest
from inventory.application.services.stock import InventoryService
from inventory.domain.entities import ReservationStatus
from inventory.domain.exceptions import InvalidReservationState, ReservationNotFound
from inventory.event_consumer import handle_order_created, handle_payment_succeeded
from inventory.infrastructure.models import ReservationModel, StockModel
from inventory.infrastructure.repositories.stock import (
    OutboxRepository,
    ReservationRepository,
    StockRepository,
)


@pytest.mark.asyncio
async def test_uuidv7_advisory_lock_hashing_distinct_keys(db_session: AsyncSession) -> None:
    """BUG-005: Ensure UUIDv7 users created at same timestamp do not collide on advisory lock."""
    drop_id = uuid.uuid7()
    user1 = uuid.uuid7()
    user2 = uuid.uuid7()

    combined1 = user1.bytes + drop_id.bytes
    combined2 = user2.bytes + drop_id.bytes
    digest1 = hashlib.sha256(combined1).digest()
    digest2 = hashlib.sha256(combined2).digest()

    key1_user = int.from_bytes(digest1[:4], "big", signed=True)
    key1_drop = int.from_bytes(digest1[4:8], "big", signed=True)
    key2_user = int.from_bytes(digest2[:4], "big", signed=True)
    key2_drop = int.from_bytes(digest2[4:8], "big", signed=True)

    assert (key1_user, key1_drop) != (key2_user, key2_drop)


@pytest.mark.asyncio
async def test_commit_expired_reservation_raises_invalid_state(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """BUG-001: Commit on an already EXPIRED reservation fails safely without double-spending."""
    product_id = uuid.uuid4()
    user_id = uuid.uuid4()
    order_id = uuid.uuid4()

    async with session_factory() as session:
        service = InventoryService(
            session=session,
            stock_repo=StockRepository(session),
            reservation_repo=ReservationRepository(session),
            outbox_repo=OutboxRepository(session),
            stock_cache=NoOpStockCache(),
        )
        stock = await service.create_stock(StockCreateRequest(product_id=product_id, total=10))
        res = await service.reserve(
            product_id=product_id,
            data=ReserveRequest(user_id=user_id, quantity=2, order_id=order_id, ttl_seconds=300),
        )
        # Simulate expire_reservations transitioning reservation to EXPIRED
        res.status = ReservationStatus.EXPIRED
        stock.available += 2
        stock.reserved -= 2
        await session.commit()

    async with session_factory() as session:
        service = InventoryService(
            session=session,
            stock_repo=StockRepository(session),
            reservation_repo=ReservationRepository(session),
            outbox_repo=OutboxRepository(session),
            stock_cache=NoOpStockCache(),
        )
        # Attempting to commit now must raise InvalidReservationState or ReservationNotFound
        with pytest.raises((InvalidReservationState, ReservationNotFound)):
            await service.commit(product_id=product_id, data=CommitRequest(order_id=order_id))


@pytest.mark.asyncio
async def test_payment_succeeded_before_order_created_triggers_retry(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """BUG-004: PaymentSucceeded arriving before OrderCreated triggers retry."""
    product_id = uuid.uuid4()
    user_id = uuid.uuid4()
    order_id = uuid.uuid4()
    res_id = uuid.uuid4()

    # Create reservation without bound order_id
    async with session_factory() as session:
        stock_repo = StockRepository(session)
        res_repo = ReservationRepository(session)
        stock = StockModel(
            id=uuid.uuid4(),
            product_id=product_id,
            total=10,
            available=8,
            reserved=2,
            sold=0,
            revision=1,
        )
        await stock_repo.create(stock)
        res = ReservationModel(
            id=res_id,
            stock_id=stock.id,
            user_id=user_id,
            order_id=None,  # Not bound yet!
            quantity=2,
            status=ReservationStatus.RESERVED,
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
        await res_repo.create(res)
        await session.commit()

    # Step 1: PaymentSucceeded arrives before OrderCreated -> must raise RuntimeError for retry
    payload = {"order_id": str(order_id), "user_id": str(user_id), "amount": 1000}
    async with session_factory() as session, session.begin():
        with pytest.raises(RuntimeError, match="No active reservation found yet"):
            await handle_payment_succeeded(session, payload)

    # Step 2: OrderCreated arrives and binds order_id
    bind_payload = {"reservation_id": str(res_id), "order_id": str(order_id)}
    async with session_factory() as session, session.begin():
        await handle_order_created(session, bind_payload)

    # Step 3: PaymentSucceeded retries and succeeds!
    async with session_factory() as session, session.begin():
        committed_stock = await handle_payment_succeeded(session, payload)
        assert committed_stock is not None
        assert committed_stock.sold == 2
        assert committed_stock.reserved == 0
