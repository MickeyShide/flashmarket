"""HTTP-level tests for stock and reservation endpoints."""

import uuid

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from inventory.infrastructure.models import OutboxEventModel, StockModel


async def _create_stock(
    client: AsyncClient,
    product_id: uuid.UUID | None = None,
    total: int = 100,
) -> dict[str, object]:
    payload = {
        "product_id": str(product_id or uuid.uuid7()),
        "total": total,
    }
    resp = await client.post("/api/v1/stocks", json=payload)
    assert resp.status_code == 201
    data: dict[str, object] = resp.json()
    return data


async def test_create_stock_201(client: AsyncClient) -> None:
    """POST /api/v1/stocks returns 201 with correct counters."""
    product_id = uuid.uuid7()
    resp = await client.post(
        "/api/v1/stocks",
        json={"product_id": str(product_id), "total": 100},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["product_id"] == str(product_id)
    assert data["total"] == 100
    assert data["available"] == 100
    assert data["reserved"] == 0
    assert data["sold"] == 0
    assert "revision" not in data


async def test_get_stock_200(client: AsyncClient) -> None:
    """GET /api/v1/stocks/{product_id} returns stock."""
    stock = await _create_stock(client, total=50)
    resp = await client.get(f"/api/v1/stocks/{stock['product_id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 50


async def test_get_stock_404(client: AsyncClient) -> None:
    """GET /api/v1/stocks/{product_id} returns 404 for unknown product."""
    resp = await client.get(f"/api/v1/stocks/{uuid.uuid7()}")
    assert resp.status_code == 404


async def test_reserve_201(client: AsyncClient, db_session: AsyncSession) -> None:
    """POST /api/v1/stocks/{product_id}/reserve decrements available."""
    stock = await _create_stock(client, total=10)
    user_id = uuid.uuid7()

    resp = await client.post(
        f"/api/v1/stocks/{stock['product_id']}/reserve",
        json={"user_id": str(user_id), "quantity": 2},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["reservation"]["quantity"] == 2
    assert data["reservation"]["user_id"] == str(user_id)
    assert data["stock"]["available"] == 8
    assert data["stock"]["reserved"] == 2

    result = await db_session.scalars(select(OutboxEventModel))
    events = result.all()
    assert len(events) == 1
    assert events[0].event_type == "InventoryReserved"


async def test_reserve_out_of_stock_409(client: AsyncClient) -> None:
    """Reserving more than available returns 409."""
    stock = await _create_stock(client, total=1)
    resp = await client.post(
        f"/api/v1/stocks/{stock['product_id']}/reserve",
        json={"user_id": str(uuid.uuid7()), "quantity": 2},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "out_of_stock"


async def test_commit_200(client: AsyncClient, db_session: AsyncSession) -> None:
    """POST /api/v1/stocks/{product_id}/commit converts reservation to sale."""
    stock = await _create_stock(client, total=10)
    order_id = uuid.uuid7()
    user_id = uuid.uuid7()

    resp = await client.post(
        f"/api/v1/stocks/{stock['product_id']}/reserve",
        json={"user_id": str(user_id), "quantity": 2, "order_id": str(order_id)},
    )
    assert resp.status_code == 201

    resp = await client.post(
        f"/api/v1/stocks/{stock['product_id']}/commit",
        json={"order_id": str(order_id)},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "COMMITTED"

    product_id_str: str = stock["product_id"]  # type: ignore[assignment]
    stock_result = await db_session.scalar(
        select(StockModel).where(StockModel.product_id == uuid.UUID(product_id_str))
    )
    assert stock_result is not None
    assert stock_result.reserved == 0
    assert stock_result.sold == 2
    assert stock_result.available == 8

    result = await db_session.scalars(
        select(OutboxEventModel).where(OutboxEventModel.event_type == "InventoryCommitted")
    )
    assert len(result.all()) == 1


async def test_release_200(client: AsyncClient, db_session: AsyncSession) -> None:
    """POST /api/v1/stocks/{product_id}/release returns stock."""
    stock = await _create_stock(client, total=10)
    order_id = uuid.uuid7()

    await client.post(
        f"/api/v1/stocks/{stock['product_id']}/reserve",
        json={"user_id": str(uuid.uuid7()), "quantity": 3, "order_id": str(order_id)},
    )

    resp = await client.post(
        f"/api/v1/stocks/{stock['product_id']}/release",
        json={"order_id": str(order_id)},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "RELEASED"

    product_id_str: str = stock["product_id"]  # type: ignore[assignment]
    stock_result = await db_session.scalar(
        select(StockModel).where(StockModel.product_id == uuid.UUID(product_id_str))
    )
    assert stock_result is not None
    assert stock_result.reserved == 0
    assert stock_result.available == 10


async def test_serial_reservations_no_oversell(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Reserving up to total succeeds; the next attempt fails with 409."""
    stock = await _create_stock(client, total=5)
    product_id = stock["product_id"]

    for _ in range(5):
        resp = await client.post(
            f"/api/v1/stocks/{product_id}/reserve",
            json={"user_id": str(uuid.uuid7()), "quantity": 1},
        )
        assert resp.status_code == 201

    resp = await client.post(
        f"/api/v1/stocks/{product_id}/reserve",
        json={"user_id": str(uuid.uuid7()), "quantity": 1},
    )
    assert resp.status_code == 409

    product_id_str: str = product_id  # type: ignore[assignment]
    stock_result = await db_session.scalar(
        select(StockModel).where(StockModel.product_id == uuid.UUID(product_id_str))
    )
    assert stock_result is not None
    assert stock_result.reserved == 5
    assert stock_result.available == 0
