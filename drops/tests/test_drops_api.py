"""Integration tests for Drops API endpoints."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_drop_201(client: AsyncClient) -> None:
    now = datetime.now(UTC)
    payload = {
        "name": "Spring Flash Sale",
        "slug": "spring-flash-sale",
        "description": "Exclusive drop",
        "starts_at": (now + timedelta(hours=2)).isoformat(),
        "ends_at": (now + timedelta(hours=6)).isoformat(),
        "max_per_user": 1,
        "payment_timeout_seconds": 300,
    }

    response = await client.post("/api/v1/admin/drops/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Spring Flash Sale"
    assert data["slug"] == "spring-flash-sale"
    assert data["status"] == "DRAFT"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_duplicate_slug_409(client: AsyncClient) -> None:
    now = datetime.now(UTC)
    payload = {
        "name": "Drop A",
        "slug": "dup-slug-api",
        "starts_at": (now + timedelta(hours=2)).isoformat(),
        "ends_at": (now + timedelta(hours=6)).isoformat(),
    }

    await client.post("/api/v1/admin/drops/", json=payload)
    response = await client.post("/api/v1/admin/drops/", json=payload)

    assert response.status_code == 409
    data = response.json()
    assert data["error"]["code"] == "duplicate_drop_slug"


@pytest.mark.asyncio
async def test_schedule_and_start_endpoints(client: AsyncClient) -> None:
    now = datetime.now(UTC)
    payload = {
        "name": "Drop transitions",
        "slug": "transitions-slug",
        "starts_at": (now + timedelta(hours=2)).isoformat(),
        "ends_at": (now + timedelta(hours=6)).isoformat(),
    }

    res_create = await client.post("/api/v1/admin/drops/", json=payload)
    drop_id = res_create.json()["id"]

    res_sched = await client.post(f"/api/v1/admin/drops/{drop_id}/schedule")
    assert res_sched.status_code == 200
    assert res_sched.json()["status"] == "SCHEDULED"

    res_start = await client.post(f"/api/v1/admin/drops/{drop_id}/start")
    assert res_start.status_code == 200
    assert res_start.json()["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_public_active_and_upcoming_endpoints(client: AsyncClient) -> None:
    now = datetime.now(UTC)

    # 1. Create and active drop
    res1 = await client.post(
        "/api/v1/admin/drops/",
        json={
            "name": "Active Drop",
            "slug": "public-active",
            "starts_at": (now + timedelta(hours=1)).isoformat(),
            "ends_at": (now + timedelta(hours=5)).isoformat(),
        },
    )
    d1_id = res1.json()["id"]
    await client.post(f"/api/v1/admin/drops/{d1_id}/schedule")
    await client.post(f"/api/v1/admin/drops/{d1_id}/start")

    # 2. Create an upcoming drop
    res2 = await client.post(
        "/api/v1/admin/drops/",
        json={
            "name": "Upcoming Drop",
            "slug": "public-upcoming",
            "starts_at": (now + timedelta(hours=1)).isoformat(),
            "ends_at": (now + timedelta(hours=5)).isoformat(),
        },
    )
    d2_id = res2.json()["id"]
    await client.post(f"/api/v1/admin/drops/{d2_id}/schedule")

    # 3. Test public active
    res_active = await client.get("/api/v1/drops/active")
    assert res_active.status_code == 200
    active_slugs = [d["slug"] for d in res_active.json()]
    assert "public-active" in active_slugs

    # 4. Test public upcoming
    res_upcoming = await client.get("/api/v1/drops/upcoming")
    assert res_upcoming.status_code == 200
    upcoming_slugs = [d["slug"] for d in res_upcoming.json()]
    assert "public-upcoming" in upcoming_slugs


@pytest.mark.asyncio
async def test_add_and_remove_drop_items_api(client: AsyncClient) -> None:
    now = datetime.now(UTC)
    res = await client.post(
        "/api/v1/admin/drops/",
        json={
            "name": "Item drop api",
            "slug": "item-drop-api",
            "starts_at": (now + timedelta(hours=1)).isoformat(),
            "ends_at": (now + timedelta(hours=5)).isoformat(),
        },
    )
    drop_id = res.json()["id"]
    prod_id = uuid.uuid4()

    res_add = await client.post(
        f"/api/v1/admin/drops/{drop_id}/items",
        json={"product_id": str(prod_id), "sort_order": 1},
    )
    assert res_add.status_code == 201
    assert res_add.json()["product_id"] == str(prod_id)

    res_del = await client.delete(
        f"/api/v1/admin/drops/{drop_id}/items/{prod_id}"
    )
    assert res_del.status_code == 204
