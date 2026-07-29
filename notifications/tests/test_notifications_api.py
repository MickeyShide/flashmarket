"""HTTP-level tests for notification endpoints."""

import uuid

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from notifications.infrastructure.models import OutboxEventModel


async def _create_notification(
    client: AsyncClient,
    user_id: uuid.UUID | None = None,
    recipient: str = "user@example.com",
) -> dict[str, object]:
    payload = {
        "user_id": str(user_id or uuid.uuid7()),
        "channel": "EMAIL",
        "subject": "Order confirmed",
        "body": "Your order has been confirmed.",
        "recipient": recipient,
    }
    resp = await client.post("/api/v1/notifications", json=payload)
    assert resp.status_code == 201
    data: dict[str, object] = resp.json()
    return data


async def test_create_notification_201(client: AsyncClient) -> None:
    """POST /api/v1/notifications returns 201 with PENDING status."""
    notification = await _create_notification(client)
    assert notification["status"] == "PENDING"
    assert notification["subject"] == "Order confirmed"


async def test_get_notification_200(client: AsyncClient) -> None:
    """GET /api/v1/notifications/{id} returns the notification."""
    notification = await _create_notification(client)
    resp = await client.get(f"/api/v1/notifications/{notification['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == notification["id"]


async def test_get_notification_404(client: AsyncClient) -> None:
    """GET /api/v1/notifications/{id} returns 404 for unknown notification."""
    resp = await client.get(f"/api/v1/notifications/{uuid.uuid7()}")
    assert resp.status_code == 404


async def test_send_notification_200(client: AsyncClient, db_session: AsyncSession) -> None:
    """POST /api/v1/notifications/{id}/send marks notification sent."""
    notification = await _create_notification(client)

    resp = await client.post(f"/api/v1/notifications/{notification['id']}/send")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SENT"
    assert data["sent_at"] is not None

    result = await db_session.scalars(
        select(OutboxEventModel).where(OutboxEventModel.event_type == "NotificationSent")
    )
    assert len(result.all()) == 1


async def test_fail_notification_200(client: AsyncClient) -> None:
    """POST /api/v1/notifications/{id}/fail marks notification failed."""
    notification = await _create_notification(client)

    resp = await client.post(
        f"/api/v1/notifications/{notification['id']}/fail",
        params={"reason": "bounce"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "FAILED"
    assert data["last_error"] == "bounce"
    assert data["attempts"] == 1


async def test_send_already_failed_notification_409(client: AsyncClient) -> None:
    """Sending a failed notification returns 409."""
    notification = await _create_notification(client)

    resp = await client.post(
        f"/api/v1/notifications/{notification['id']}/fail",
        params={"reason": "bounce"},
    )
    assert resp.status_code == 200

    resp = await client.post(f"/api/v1/notifications/{notification['id']}/send")
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "invalid_notification_state"


async def test_list_user_notifications(client: AsyncClient) -> None:
    """GET /api/v1/notifications/users/{user_id} returns paginated items."""
    user_id = uuid.uuid7()
    for _ in range(3):
        await _create_notification(client, user_id=user_id)

    resp = await client.get(f"/api/v1/notifications/users/{user_id}", params={"limit": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] == 3
