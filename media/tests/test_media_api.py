"""HTTP contract and lifecycle tests using fake S3."""

from io import BytesIO
from uuid import UUID, uuid4

from httpx import AsyncClient
from PIL import Image

from tests.conftest import FakeStorage


def png_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (4, 5), "blue").save(output, format="PNG")
    return output.getvalue()


async def create_upload(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    purpose: str = "review_image",
    entity_type: str | None = None,
    entity_id: str | None = None,
    content: bytes | None = None,
) -> tuple[dict[str, object], bytes]:
    body = content or png_bytes()
    response = await client.post(
        "/api/v1/media/uploads",
        headers=headers,
        json={
            "purpose": purpose,
            "filename": "picture.png",
            "content_type": "image/png",
            "size": len(body),
            "entity_type": entity_type,
            "entity_id": entity_id,
        },
    )
    assert response.status_code == 201, response.text
    return response.json(), body


async def test_admin_upload_complete_and_anonymous_read(
    client: AsyncClient,
    fake_storage: FakeStorage,
    auth_headers,  # type: ignore[no-untyped-def]
) -> None:
    headers = auth_headers(role="ADMIN")
    product_id = str(uuid4())
    created, content = await create_upload(
        client,
        headers,
        purpose="product_image",
        entity_type="product",
        entity_id=product_id,
    )
    asset = created["asset"]
    assert isinstance(asset, dict)
    asset_id = str(asset["id"])
    key = str(created["upload"]["fields"]["key"])  # type: ignore[index]
    fake_storage.upload(key, content, "image/png", asset_id)

    completed = await client.post(f"/api/v1/media/assets/{asset_id}/complete", headers=headers)
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "READY"
    assert completed.json()["width"] == 4
    assert completed.json()["public_url"].startswith("https://media.test/test-public/")

    public = await client.get(f"/api/v1/media/assets/{asset_id}")
    assert public.status_code == 200
    assert public.json()["sha256"] == completed.json()["sha256"]

    entity = await client.get(f"/api/v1/media/entities/product/{product_id}/assets")
    assert entity.status_code == 200
    assert entity.json()["total"] == 1


async def test_customer_cannot_upload_product_or_another_users_avatar(
    client: AsyncClient,
    auth_headers,  # type: ignore[no-untyped-def]
) -> None:
    user_id = uuid4()
    headers = auth_headers(user_id=user_id)
    product = await client.post(
        "/api/v1/media/uploads",
        headers=headers,
        json={
            "purpose": "product_image",
            "filename": "x.png",
            "content_type": "image/png",
            "size": 20,
            "entity_type": "product",
            "entity_id": str(uuid4()),
        },
    )
    assert product.status_code == 403

    avatar = await client.post(
        "/api/v1/media/uploads",
        headers=headers,
        json={
            "purpose": "user_avatar",
            "filename": "x.png",
            "content_type": "image/png",
            "size": 20,
            "entity_type": "user",
            "entity_id": str(uuid4()),
        },
    )
    assert avatar.status_code == 403


async def test_non_ready_asset_is_private_to_owner(
    client: AsyncClient,
    auth_headers,  # type: ignore[no-untyped-def]
) -> None:
    headers = auth_headers()
    created, _ = await create_upload(client, headers)
    asset_id = created["asset"]["id"]  # type: ignore[index]
    assert (await client.get(f"/api/v1/media/assets/{asset_id}")).status_code == 404
    assert (
        await client.get(f"/api/v1/media/assets/{asset_id}", headers=headers)
    ).status_code == 200


async def test_mismatched_bytes_are_rejected_and_removed(
    client: AsyncClient,
    fake_storage: FakeStorage,
    auth_headers,  # type: ignore[no-untyped-def]
) -> None:
    headers = auth_headers()
    created, content = await create_upload(client, headers)
    asset_id = str(created["asset"]["id"])  # type: ignore[index]
    key = str(created["upload"]["fields"]["key"])  # type: ignore[index]
    fake_storage.upload(key, content, "image/jpeg", asset_id)
    response = await client.post(f"/api/v1/media/assets/{asset_id}/complete", headers=headers)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "unsupported_content_type"
    assert key not in fake_storage.objects


async def test_review_binding_listing_and_eventual_delete(
    client: AsyncClient,
    fake_storage: FakeStorage,
    auth_headers,  # type: ignore[no-untyped-def]
) -> None:
    headers = auth_headers()
    created, content = await create_upload(client, headers)
    asset_id = str(created["asset"]["id"])  # type: ignore[index]
    key = str(created["upload"]["fields"]["key"])  # type: ignore[index]
    fake_storage.upload(key, content, "image/png", asset_id)
    await client.post(f"/api/v1/media/assets/{asset_id}/complete", headers=headers)

    review_id = uuid4()
    bound = await client.patch(
        f"/api/v1/media/assets/{asset_id}/binding",
        headers=headers,
        json={"entity_type": "review", "entity_id": str(review_id)},
    )
    assert bound.status_code == 200
    assert UUID(bound.json()["entity_id"]) == review_id

    mine = await client.get("/api/v1/media/assets/mine", headers=headers)
    assert mine.status_code == 200
    assert mine.json()["total"] == 1

    deleted = await client.delete(f"/api/v1/media/assets/{asset_id}", headers=headers)
    assert deleted.status_code == 202
    assert deleted.json()["status"] == "DELETING"


async def test_health_checks_database_and_storage(
    client: AsyncClient, fake_storage: FakeStorage
) -> None:
    assert (await client.get("/health/live")).status_code == 200
    assert (await client.get("/health/ready")).status_code == 200
    fake_storage.available = False
    assert (await client.get("/health/ready")).status_code == 503


async def test_admin_can_filter_all_assets(
    client: AsyncClient,
    auth_headers,  # type: ignore[no-untyped-def]
) -> None:
    customer_headers = auth_headers()
    await create_upload(client, customer_headers)
    denied = await client.get("/api/v1/media/admin/assets", headers=customer_headers)
    assert denied.status_code == 403

    admin = await client.get(
        "/api/v1/media/admin/assets",
        headers=auth_headers(role="ADMIN"),
        params={"asset_status": "PENDING", "purpose": "review_image"},
    )
    assert admin.status_code == 200
    assert admin.json()["total"] == 1
