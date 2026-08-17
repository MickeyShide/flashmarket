"""Deep business rules, state transition, and atomicity tests for orders service."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from orders.application.schemas import CreateOrderBatchRequest, CreateOrderRequest
from orders.application.services.order import OrderService
from orders.application.services.promocode import PromocodeService
from orders.domain.entities import DiscountType, OrderStatus, PromocodeStatus
from orders.domain.exceptions import (
    InvalidOrderState,
    PromocodeLimitReached,
)
from orders.infrastructure.catalog_client import CatalogClient, CatalogProductPrice
from orders.infrastructure.models import OrderModel, OutboxEventModel, PromocodeModel
from orders.infrastructure.repositories.order import OrderRepository, OutboxRepository
from orders.infrastructure.repositories.promocode import PromocodeRepository


@pytest.mark.asyncio
async def test_promocode_usage_exhaustion_rejects_subsequent_orders(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """A max_uses=1 promocode is consumed by the first order and rejected on subsequent orders."""
    promo_id = uuid.uuid7()
    code = "ONEUSEONLY"
    now = datetime.now(UTC)

    # 1. Setup single-use promo code
    async with session_factory() as session:
        promo_repo = PromocodeRepository(session)
        promo = PromocodeModel(
            id=promo_id,
            code=code,
            discount_type=DiscountType.FIXED,
            discount_value=Decimal("500.00"),
            max_uses=1,
            current_uses=0,
            status=PromocodeStatus.ACTIVE,
            starts_at=now - timedelta(hours=1),
            expires_at=now + timedelta(hours=1),
        )
        await promo_repo.create(promo)
        await session.commit()

    # 2. First order consumes the single use
    async with session_factory() as session:
        order_service = OrderService(
            session=session,
            order_repo=OrderRepository(session),
            outbox_repo=OutboxRepository(session),
            promocode_service=PromocodeService(session, PromocodeRepository(session)),
        )
        order1 = await order_service.create_order(
            CreateOrderRequest(
                user_id=uuid.uuid7(),
                product_id=uuid.uuid7(),
                product_name="Item 1",
                price=2000,
                currency="RUB",
                quantity=1,
                reservation_id=uuid.uuid7(),
                promocode=code,
            )
        )
        assert order1.discount_amount == Decimal("500.00")

    # 3. Second order attempting to use the same code is rejected
    async with session_factory() as session:
        order_service = OrderService(
            session=session,
            order_repo=OrderRepository(session),
            outbox_repo=OutboxRepository(session),
            promocode_service=PromocodeService(session, PromocodeRepository(session)),
        )
        with pytest.raises(PromocodeLimitReached):
            await order_service.create_order(
                CreateOrderRequest(
                    user_id=uuid.uuid7(),
                    product_id=uuid.uuid7(),
                    product_name="Item 2",
                    price=2000,
                    currency="RUB",
                    quantity=1,
                    reservation_id=uuid.uuid7(),
                    promocode=code,
                )
            )

    # 4. Verify DB count remains 1
    async with session_factory() as session:
        promo_db = await PromocodeRepository(session).get_by_id(promo_id)
        assert promo_db is not None
        assert promo_db.current_uses == 1


@pytest.mark.asyncio
async def test_invalid_order_state_transitions_raise_exception(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Attempting invalid state transitions raises InvalidOrderState."""
    order_id = uuid.uuid7()

    # 1. Create already confirmed order
    async with session_factory() as session:
        order = OrderModel(
            id=order_id,
            user_id=uuid.uuid7(),
            product_id=uuid.uuid7(),
            product_name="Confirmed Item",
            price=1500,
            currency="RUB",
            quantity=1,
            status=OrderStatus.CONFIRMED,
            reservation_id=uuid.uuid7(),
        )
        await OrderRepository(session).create(order)
        await session.commit()

    # Attempting to cancel a confirmed order must raise InvalidOrderState
    async with session_factory() as session:
        order_service = OrderService(
            session=session,
            order_repo=OrderRepository(session),
            outbox_repo=OutboxRepository(session),
        )
        with pytest.raises(InvalidOrderState):
            await order_service.cancel_order(order_id)


@pytest.mark.asyncio
async def test_batch_creation_atomicity_rolls_back_on_single_mismatch(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """When 1 line in a batch fails catalog price validation, entire batch is rolled back."""
    user_id = uuid.uuid7()
    prod_valid_1 = uuid.uuid7()
    prod_invalid_2 = uuid.uuid7()

    mock_catalog = AsyncMock(spec=CatalogClient)

    async def get_price(pid: uuid.UUID) -> CatalogProductPrice | None:
        if pid == prod_valid_1:
            return CatalogProductPrice(product_id=prod_valid_1, price=1000, currency="RUB")
        if pid == prod_invalid_2:
            return CatalogProductPrice(product_id=prod_invalid_2, price=9999, currency="RUB")
        return None

    mock_catalog.get_price.side_effect = get_price

    batch_req = CreateOrderBatchRequest(
        lines=[
            CreateOrderRequest(
                user_id=user_id,
                product_id=prod_valid_1,
                product_name="Valid Item",
                price=1000,
                quantity=1,
                reservation_id=uuid.uuid7(),
                currency="RUB",
            ),
            CreateOrderRequest(
                user_id=user_id,
                product_id=prod_invalid_2,
                product_name="Tampered Item",
                price=1,  # Authoritative price is 9999!
                quantity=1,
                reservation_id=uuid.uuid7(),
                currency="RUB",
            ),
        ],
    )

    async with session_factory() as session:
        order_service = OrderService(
            session=session,
            order_repo=OrderRepository(session),
            outbox_repo=OutboxRepository(session),
            catalog_client=mock_catalog,
        )
        with pytest.raises(InvalidOrderState, match="Price mismatch"):
            await order_service.create_batch(batch_req)

    # Verify zero orders and zero outbox events were created
    async with session_factory() as session:
        orders = await session.scalars(select(OrderModel))
        assert len(orders.all()) == 0
        events = await session.scalars(select(OutboxEventModel))
        assert len(events.all()) == 0
