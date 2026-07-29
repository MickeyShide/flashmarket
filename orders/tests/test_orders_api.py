"""HTTP-level tests for order endpoints."""

import uuid

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from orders.infrastructure.models import OutboxEventModel


async def _create_order(
    client: AsyncClient,
    user_id: uuid.UUID | None = None,
    reservation_id: uuid.UUID | None = None,
) -> dict[str, object]:
    payload = {
        "user_id": str(user_id or uuid.uuid7()),
        "product_id": str(uuid.uuid7()),
        "product_name": "Nike Air Max Limited",
        "price": 12990,
        "currency": "RUB",
        "quantity": 1,
        "reservation_id": str(reservation_id or uuid.uuid7()),
    }
    resp = await client.post("/api/v1/orders", json=payload)
    assert resp.status_code == 201
    data: dict[str, object] = resp.json()
    return data


async def test_create_order_201(client: AsyncClient, db_session: AsyncSession) -> None:
    """POST /api/v1/orders returns 201 with awaiting_payment status."""
    order = await _create_order(client)
    assert order["status"] == "AWAITING_PAYMENT"
    assert order["product_name"] == "Nike Air Max Limited"

    result = await db_session.scalars(select(OutboxEventModel))
    events = result.all()
    assert len(events) == 2
    assert {e.event_type for e in events} == {"OrderCreated", "PaymentRequested"}


async def test_create_order_duplicate_reservation_409(client: AsyncClient) -> None:
    """Creating two orders for the same reservation returns 409."""
    reservation_id = uuid.uuid7()
    await _create_order(client, reservation_id=reservation_id)
    payload = {
        "user_id": str(uuid.uuid7()),
        "product_id": str(uuid.uuid7()),
        "product_name": "Nike Air Max Limited",
        "price": 12990,
        "currency": "RUB",
        "quantity": 1,
        "reservation_id": str(reservation_id),
    }
    resp = await client.post("/api/v1/orders", json=payload)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "duplicate_order"


async def test_get_order_200(client: AsyncClient) -> None:
    """GET /api/v1/orders/{order_id} returns the order."""
    order = await _create_order(client)
    resp = await client.get(f"/api/v1/orders/{order['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == order["id"]


async def test_get_order_404(client: AsyncClient) -> None:
    """GET /api/v1/orders/{order_id} returns 404 for unknown order."""
    resp = await client.get(f"/api/v1/orders/{uuid.uuid7()}")
    assert resp.status_code == 404


async def test_confirm_order_200(client: AsyncClient, db_session: AsyncSession) -> None:
    """POST /api/v1/orders/{order_id}/confirm marks order confirmed."""
    order = await _create_order(client)
    payment_id = uuid.uuid7()

    resp = await client.post(
        f"/api/v1/orders/{order['id']}/confirm",
        params={"payment_id": str(payment_id)},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "CONFIRMED"
    assert data["payment_id"] == str(payment_id)

    result = await db_session.scalars(
        select(OutboxEventModel).where(OutboxEventModel.event_type == "OrderConfirmed")
    )
    assert len(result.all()) == 1


async def test_fail_order_200(client: AsyncClient, db_session: AsyncSession) -> None:
    """POST /api/v1/orders/{order_id}/fail marks order cancelled."""
    order = await _create_order(client)
    payment_id = uuid.uuid7()

    resp = await client.post(
        f"/api/v1/orders/{order['id']}/fail",
        params={"payment_id": str(payment_id)},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "CANCELLED"

    result = await db_session.scalars(
        select(OutboxEventModel).where(OutboxEventModel.event_type == "OrderCancelled")
    )
    assert len(result.all()) == 1


async def test_confirm_already_failed_order_409(client: AsyncClient) -> None:
    """Confirming a cancelled order returns 409."""
    order = await _create_order(client)
    payment_id = uuid.uuid7()

    resp = await client.post(
        f"/api/v1/orders/{order['id']}/fail",
        params={"payment_id": str(payment_id)},
    )
    assert resp.status_code == 200

    resp = await client.post(
        f"/api/v1/orders/{order['id']}/confirm",
        params={"payment_id": str(uuid.uuid7())},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "invalid_order_state"


async def test_list_user_orders(client: AsyncClient) -> None:
    """GET /api/v1/orders returns paginated user orders."""
    user_id = uuid.uuid7()
    for _ in range(3):
        await _create_order(client, user_id=user_id)

    resp = await client.get(f"/api/v1/orders/users/{user_id}", params={"limit": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
