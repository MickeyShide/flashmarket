"""Regression tests for orders security and business logic fixes."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from jwt_verifier.testing import TestKeyStore
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from orders.application.schemas import CreateOrderRequest
from orders.application.services.order import OrderService
from orders.application.services.promocode import PromocodeService
from orders.domain.entities import DiscountType, OrderStatus, PromocodeStatus
from orders.domain.exceptions import DuplicateOrder, InvalidOrderState
from orders.event_consumer import handle_payment_succeeded
from orders.infrastructure.catalog_client import CatalogClient, CatalogProductPrice
from orders.infrastructure.models import OrderModel, PromocodeModel, PromocodeUsageModel
from orders.infrastructure.repositories.order import OrderRepository, OutboxRepository
from orders.infrastructure.repositories.promocode import PromocodeRepository
from orders.main import app


@pytest.fixture
async def customer_client(
    session_factory: async_sessionmaker[AsyncSession],
    jwt_keystore: TestKeyStore,
) -> AsyncClient:
    """Provide an HTTP client authenticated as a regular CUSTOMER."""
    del session_factory
    token = jwt_keystore.create_token(role="CUSTOMER")
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://localhost", headers=headers
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_customer_cannot_confirm_order_via_endpoint(
    client: AsyncClient, customer_client: AsyncClient
) -> None:
    """BUG-003: Public order confirmation endpoint must forbid non-admin customers."""
    # Create order via admin client
    res = await client.post(
        "/api/v1/orders",
        json={
            "user_id": str(uuid.uuid7()),
            "product_id": str(uuid.uuid7()),
            "product_name": "Test Item",
            "price": 5000,
            "currency": "RUB",
            "quantity": 1,
            "reservation_id": str(uuid.uuid7()),
        },
    )
    assert res.status_code == 201
    order_id = res.json()["id"]

    # Customer attempt to confirm must receive 403 Forbidden
    confirm_res = await customer_client.post(
        f"/api/v1/orders/{order_id}/confirm",
        params={"payment_id": str(uuid.uuid7())},
    )
    assert confirm_res.status_code == 403


@pytest.mark.asyncio
async def test_order_price_tampering_rejected_by_catalog_client(
    db_session: AsyncSession,
) -> None:
    """BUG-002: Client-supplied price differing from catalog price is rejected."""
    product_id = uuid.uuid7()
    mock_catalog = AsyncMock(spec=CatalogClient)
    mock_catalog.get_price.return_value = CatalogProductPrice(
        product_id=product_id,
        price=10000,
        currency="RUB",
    )

    service = OrderService(
        session=db_session,
        order_repo=OrderRepository(db_session),
        outbox_repo=OutboxRepository(db_session),
        catalog_client=mock_catalog,
    )

    # Client tries to purchase 10,000 RUB product for 1 RUB
    tampered_request = CreateOrderRequest(
        user_id=uuid.uuid7(),
        product_id=product_id,
        product_name="Luxury Item",
        price=1,  # Injected exploit!
        currency="RUB",
        quantity=1,
        reservation_id=uuid.uuid7(),
    )

    with pytest.raises(InvalidOrderState, match="Price mismatch"):
        await service.create_order(tampered_request)


@pytest.mark.asyncio
async def test_duplicate_reservation_id_rejected(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """BUG-007: Duplicate reservation_id raises DuplicateOrder."""
    reservation_id = uuid.uuid7()
    product_id = uuid.uuid7()
    user_id = uuid.uuid7()

    async with session_factory() as session:
        service = OrderService(
            session=session,
            order_repo=OrderRepository(session),
            outbox_repo=OutboxRepository(session),
        )
        req1 = CreateOrderRequest(
            user_id=user_id,
            product_id=product_id,
            product_name="Product",
            price=1000,
            currency="RUB",
            quantity=1,
            reservation_id=reservation_id,
        )
        await service.create_order(req1)

    async with session_factory() as session:
        service = OrderService(
            session=session,
            order_repo=OrderRepository(session),
            outbox_repo=OutboxRepository(session),
        )
        req2 = CreateOrderRequest(
            user_id=user_id,
            product_id=product_id,
            product_name="Product",
            price=1000,
            currency="RUB",
            quantity=1,
            reservation_id=reservation_id,
        )
        with pytest.raises(DuplicateOrder):
            await service.create_order(req2)


@pytest.mark.asyncio
async def test_order_cancellation_rolls_back_promocode(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """BUG-010: Cancelled order rolls back promocode usage."""
    user_id = uuid.uuid7()
    product_id = uuid.uuid7()
    promo_id = uuid.uuid7()
    code = "DISCOUNT50"

    async with session_factory() as session:
        promo_repo = PromocodeRepository(session)
        now = datetime.now(UTC)
        promo = PromocodeModel(
            id=promo_id,
            code=code,
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal("50.00"),
            max_uses=1,
            current_uses=0,
            status=PromocodeStatus.ACTIVE,
            starts_at=now - timedelta(hours=1),
            expires_at=now + timedelta(hours=1),
        )
        await promo_repo.create(promo)
        await session.commit()

    # Step 1: Create order using promo code
    order_id = None
    async with session_factory() as session:
        promo_service = PromocodeService(session, PromocodeRepository(session))
        order_service = OrderService(
            session=session,
            order_repo=OrderRepository(session),
            outbox_repo=OutboxRepository(session),
            promocode_service=promo_service,
        )
        order = await order_service.create_order(
            CreateOrderRequest(
                user_id=user_id,
                product_id=product_id,
                product_name="Discounted Item",
                price=1000,
                currency="RUB",
                quantity=1,
                reservation_id=uuid.uuid7(),
                promocode=code,
            )
        )
        order_id = order.id
        assert order.discount_amount == Decimal("500.00")

    # Verify promo is consumed
    async with session_factory() as session:
        promo = await PromocodeRepository(session).get_by_id(promo_id)
        assert promo.current_uses == 1

    # Step 2: Cancel order
    async with session_factory() as session:
        promo_service = PromocodeService(session, PromocodeRepository(session))
        order_service = OrderService(
            session=session,
            order_repo=OrderRepository(session),
            outbox_repo=OutboxRepository(session),
            promocode_service=promo_service,
        )
        await order_service.cancel_order(order_id)

    # Step 3: Verify promo usage was rolled back
    async with session_factory() as session:
        promo = await PromocodeRepository(session).get_by_id(promo_id)
        assert promo.current_uses == 0
        usages = await session.scalars(
            select(PromocodeUsageModel).where(PromocodeUsageModel.promocode_id == promo_id)
        )
        assert len(usages.all()) == 0


@pytest.mark.asyncio
async def test_payment_succeeded_does_not_override_cancelled_order(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """BUG-009: PaymentSucceeded event does not revert an already CANCELLED order to CONFIRMED."""
    order_id = uuid.uuid7()
    user_id = uuid.uuid7()
    reservation_id = uuid.uuid7()

    async with session_factory() as session:
        order = OrderModel(
            id=order_id,
            user_id=user_id,
            product_id=uuid.uuid7(),
            product_name="Product",
            price=1000,
            currency="RUB",
            quantity=1,
            status=OrderStatus.CANCELLED,  # Order is already cancelled
            reservation_id=reservation_id,
        )
        await OrderRepository(session).create(order)
        await session.commit()

    payload = {"order_id": str(order_id), "payment_id": str(uuid.uuid7())}
    async with session_factory() as session, session.begin():
        await handle_payment_succeeded(session, payload)

    async with session_factory() as session:
        order = await OrderRepository(session).get_by_id(order_id)
        assert order.status == OrderStatus.CANCELLED
