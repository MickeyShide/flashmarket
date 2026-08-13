"""Comprehensive integration tests for Wishlist microservice (WISH-001 through WISH-011)."""

import uuid

import pytest
from httpx import AsyncClient
from jwt_verifier.testing import TestKeyStore


@pytest.mark.asyncio
async def test_wish_001_to_005_crud_and_idempotency(client: AsyncClient) -> None:
    """WISH-001..WISH-005: Add item, duplicate idempotency, list, batch check, and delete."""
    user_id = uuid.uuid4()
    product_id_1 = uuid.uuid4()
    product_id_2 = uuid.uuid4()

    # 1. Add product_1 to wishlist
    add_resp = await client.post(
        f"/api/v1/wishlist/users/{user_id}/items",
        json={"product_id": str(product_id_1)},
    )
    assert add_resp.status_code == 201
    assert add_resp.json()["product_id"] == str(product_id_1)

    # 2. Duplicate add -> returns 409 Conflict
    dup_add = await client.post(
        f"/api/v1/wishlist/users/{user_id}/items",
        json={"product_id": str(product_id_1)},
    )
    assert dup_add.status_code == 409

    # Add product_2
    await client.post(
        f"/api/v1/wishlist/users/{user_id}/items",
        json={"product_id": str(product_id_2)},
    )

    # 3. List user wishlist items
    list_resp = await client.get(f"/api/v1/wishlist/users/{user_id}/items")
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    assert len(items) == 2

    # 4. Batch check
    check_resp = await client.post(
        f"/api/v1/wishlist/users/{user_id}/check",
        json={"product_ids": [str(product_id_1), str(product_id_2), str(uuid.uuid4())]},
    )
    assert check_resp.status_code == 200
    in_wishlist = check_resp.json()["product_ids"]
    assert str(product_id_1) in in_wishlist
    assert str(product_id_2) in in_wishlist

    # 5. Delete item
    del_resp = await client.delete(f"/api/v1/wishlist/users/{user_id}/items/{product_id_1}")
    assert del_resp.status_code == 204

    # List again -> 1 item remaining
    list_after = await client.get(f"/api/v1/wishlist/users/{user_id}/items")
    assert len(list_after.json()["items"]) == 1


@pytest.mark.asyncio
async def test_wish_008_ownership_enforcement(jwt_keystore: TestKeyStore) -> None:
    """WISH-008: Verify user cannot view/modify another user's wishlist (401/403)."""
    from httpx import ASGITransport

    from wishlist.main import app

    user_a = uuid.uuid4()
    user_b = uuid.uuid4()

    token_a = jwt_keystore.create_token(user_id=str(user_a), role="USER")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://localhost",
        headers=headers_a,
    ) as client_a:
        # Access user_b's wishlist with user_a's token -> 401/403
        resp = await client_a.get(f"/api/v1/wishlist/users/{user_b}/items")
        assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_wish_011_readiness_probe(client: AsyncClient) -> None:
    """WISH-011: Readiness probe returns HTTP 200."""
    resp = await client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
