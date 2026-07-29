"""HTTP-level tests for payment endpoints."""

import uuid

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from payments.infrastructure.models import OutboxEventModel


async def _create_payment(
    client: AsyncClient,
    order_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
) -> dict[str, object]:
    payload = {
        "order_id": str(order_id or uuid.uuid7()),
        "user_id": str(user_id or uuid.uuid7()),
        "amount": 12990,
        "currency": "RUB",
        "provider": "mock",
    }
    resp = await client.post("/api/v1/payments", json=payload)
    assert resp.status_code == 201
    data: dict[str, object] = resp.json()
    return data


async def test_create_payment_201(client: AsyncClient, db_session: AsyncSession) -> None:
    """POST /api/v1/payments returns 201 with PENDING status."""
    payment = await _create_payment(client)
    assert payment["status"] == "PENDING"

    result = await db_session.scalars(select(OutboxEventModel))
    events = result.all()
    assert len(events) == 0


async def test_get_payment_200(client: AsyncClient) -> None:
    """GET /api/v1/payments/{payment_id} returns the payment."""
    payment = await _create_payment(client)
    resp = await client.get(f"/api/v1/payments/{payment['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == payment["id"]


async def test_get_payment_404(client: AsyncClient) -> None:
    """GET /api/v1/payments/{payment_id} returns 404 for unknown payment."""
    resp = await client.get(f"/api/v1/payments/{uuid.uuid7()}")
    assert resp.status_code == 404


async def test_confirm_payment_200(client: AsyncClient, db_session: AsyncSession) -> None:
    """POST /api/v1/payments/{payment_id}/confirm marks payment successful."""
    payment = await _create_payment(client)

    resp = await client.post(f"/api/v1/payments/{payment['id']}/confirm")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["external_id"] is not None

    result = await db_session.scalars(
        select(OutboxEventModel).where(OutboxEventModel.event_type == "PaymentSucceeded")
    )
    assert len(result.all()) == 1


async def test_fail_payment_200(client: AsyncClient, db_session: AsyncSession) -> None:
    """POST /api/v1/payments/{payment_id}/fail marks payment failed."""
    payment = await _create_payment(client)

    resp = await client.post(f"/api/v1/payments/{payment['id']}/fail")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "FAILED"

    result = await db_session.scalars(
        select(OutboxEventModel).where(OutboxEventModel.event_type == "PaymentFailed")
    )
    assert len(result.all()) == 1


async def test_cancel_payment_200(client: AsyncClient, db_session: AsyncSession) -> None:
    """POST /api/v1/payments/{payment_id}/cancel marks payment cancelled."""
    payment = await _create_payment(client)

    resp = await client.post(f"/api/v1/payments/{payment['id']}/cancel")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "CANCELLED"

    result = await db_session.scalars(
        select(OutboxEventModel).where(OutboxEventModel.event_type == "PaymentCancelled")
    )
    assert len(result.all()) == 1


async def test_confirm_already_failed_payment_409(client: AsyncClient) -> None:
    """Confirming a failed payment returns 409."""
    payment = await _create_payment(client)

    resp = await client.post(f"/api/v1/payments/{payment['id']}/fail")
    assert resp.status_code == 200

    resp = await client.post(f"/api/v1/payments/{payment['id']}/confirm")
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "invalid_payment_state"


async def test_list_user_payments(client: AsyncClient) -> None:
    """GET /api/v1/payments/users/{user_id} returns paginated payments."""
    user_id = uuid.uuid7()
    for _ in range(3):
        await _create_payment(client, user_id=user_id)

    resp = await client.get(f"/api/v1/payments/users/{user_id}", params={"limit": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
