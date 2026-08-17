"""Deep concurrency and invariant tests for inventory."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from inventory.application.contracts import NoOpStockCache
from inventory.application.schemas import ReserveRequest, StockCreateRequest
from inventory.application.services.stock import InventoryService
from inventory.domain.entities import ReservationStatus
from inventory.domain.exceptions import OutOfStock
from inventory.event_consumer import handle_payment_succeeded
from inventory.infrastructure.models import OutboxEventModel, ReservationModel, StockModel
from inventory.infrastructure.repositories.stock import (
    OutboxRepository,
    ReservationRepository,
    StockRepository,
)


@pytest.mark.asyncio
async def test_stock_exhaustion_to_zero_and_rejection_of_overflow(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Reservations accurately decrement available stock to 0 and strictly reject overflow."""
    product_id = uuid.uuid4()

    # Step 1: Create stock with total=2
    async with session_factory() as session:
        service = InventoryService(
            session=session,
            stock_repo=StockRepository(session),
            reservation_repo=ReservationRepository(session),
            outbox_repo=OutboxRepository(session),
            stock_cache=NoOpStockCache(),
        )
        await service.create_stock(StockCreateRequest(product_id=product_id, total=2))

    # Step 2: First reservation of 1 unit -> succeeds (available: 1, reserved: 1)
    async with session_factory() as session:
        service = InventoryService(
            session=session,
            stock_repo=StockRepository(session),
            reservation_repo=ReservationRepository(session),
            outbox_repo=OutboxRepository(session),
            stock_cache=NoOpStockCache(),
        )
        res1 = await service.reserve(
            product_id=product_id,
            data=ReserveRequest(
                user_id=uuid.uuid4(),
                quantity=1,
                order_id=uuid.uuid4(),
                ttl_seconds=300,
            ),
        )
        assert res1.status == ReservationStatus.RESERVED

    # Step 3: Second reservation of 1 unit -> succeeds (available: 0, reserved: 2)
    async with session_factory() as session:
        service = InventoryService(
            session=session,
            stock_repo=StockRepository(session),
            reservation_repo=ReservationRepository(session),
            outbox_repo=OutboxRepository(session),
            stock_cache=NoOpStockCache(),
        )
        res2 = await service.reserve(
            product_id=product_id,
            data=ReserveRequest(
                user_id=uuid.uuid4(),
                quantity=1,
                order_id=uuid.uuid4(),
                ttl_seconds=300,
            ),
        )
        assert res2.status == ReservationStatus.RESERVED

    # Step 4: Third attempt when available=0 -> raises OutOfStock
    async with session_factory() as session:
        service = InventoryService(
            session=session,
            stock_repo=StockRepository(session),
            reservation_repo=ReservationRepository(session),
            outbox_repo=OutboxRepository(session),
            stock_cache=NoOpStockCache(),
        )
        with pytest.raises(OutOfStock):
            await service.reserve(
                product_id=product_id,
                data=ReserveRequest(
                    user_id=uuid.uuid4(),
                    quantity=1,
                    order_id=uuid.uuid4(),
                    ttl_seconds=300,
                ),
            )

    # Step 5: Verify final database state and physical invariant
    async with session_factory() as session:
        stock = await StockRepository(session).get_by_product_id(product_id)
        assert stock is not None
        assert stock.total == 2
        assert stock.available == 0
        assert stock.reserved == 2
        assert stock.sold == 0
        assert stock.available + stock.reserved + stock.sold == stock.total


@pytest.mark.asyncio
async def test_reserve_failure_persists_zero_outbox_events(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """When a reservation fails due to insufficient stock, no outbox event is persisted."""
    product_id = uuid.uuid4()

    async with session_factory() as session:
        service = InventoryService(
            session=session,
            stock_repo=StockRepository(session),
            reservation_repo=ReservationRepository(session),
            outbox_repo=OutboxRepository(session),
            stock_cache=NoOpStockCache(),
        )
        await service.create_stock(StockCreateRequest(product_id=product_id, total=0))

    async with session_factory() as session:
        service = InventoryService(
            session=session,
            stock_repo=StockRepository(session),
            reservation_repo=ReservationRepository(session),
            outbox_repo=OutboxRepository(session),
            stock_cache=NoOpStockCache(),
        )
        with pytest.raises(OutOfStock):
            await service.reserve(
                product_id=product_id,
                data=ReserveRequest(
                    user_id=uuid.uuid4(),
                    quantity=1,
                    order_id=uuid.uuid4(),
                    ttl_seconds=300,
                ),
            )

    async with session_factory() as session:
        events = await session.scalars(select(OutboxEventModel))
        # Initial stock creation might create an event, but no ReservationCreated event exists
        res_events = [e for e in events.all() if "Reservation" in e.event_type]
        assert len(res_events) == 0


@pytest.mark.asyncio
async def test_duplicate_payment_succeeded_event_does_not_double_sell(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Duplicate delivery of PaymentSucceeded is idempotent and does not increment sold twice."""
    product_id = uuid.uuid4()
    user_id = uuid.uuid4()
    order_id = uuid.uuid4()
    res_id = uuid.uuid4()

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
            order_id=order_id,
            quantity=2,
            status=ReservationStatus.RESERVED,
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
        await res_repo.create(res)
        await session.commit()

    payload = {"order_id": str(order_id), "user_id": str(user_id), "amount": 2000}

    # Delivery 1
    async with session_factory() as session, session.begin():
        committed_stock = await handle_payment_succeeded(session, payload)
        assert committed_stock is not None
        assert committed_stock.sold == 2
        assert committed_stock.reserved == 0

    # Delivery 2 (Duplicate re-delivery)
    async with session_factory() as session, session.begin():
        duplicate_res = await handle_payment_succeeded(session, payload)
        assert duplicate_res is None

    # Check final stock in DB
    async with session_factory() as session:
        final_stock = await StockRepository(session).get_by_product_id(product_id)
        assert final_stock is not None
        assert final_stock.sold == 2
        assert final_stock.reserved == 0
        assert final_stock.available == 8
