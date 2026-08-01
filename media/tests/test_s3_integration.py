"""Opt-in contract test for an existing external S3/MinIO test bucket."""

import os
import uuid

import httpx
import pytest

from media_service.config import Settings
from media_service.infrastructure.s3_storage import S3ObjectStorage

pytestmark = pytest.mark.integration


def external_test_settings() -> Settings:
    """Build settings only when destructive test writes were explicitly authorized."""
    if os.getenv("MEDIA_TEST_S3_ALLOW_WRITE") != "true":
        pytest.skip("Set MEDIA_TEST_S3_ALLOW_WRITE=true for the external S3 contract test")
    required = {
        name: os.getenv(name)
        for name in (
            "MEDIA_TEST_S3_INTERNAL_ENDPOINT",
            "MEDIA_TEST_S3_PUBLIC_ENDPOINT",
            "MEDIA_TEST_S3_ACCESS_KEY",
            "MEDIA_TEST_S3_SECRET_KEY",
            "MEDIA_TEST_S3_BUCKET",
        )
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        pytest.skip("Missing external S3 test settings: " + ", ".join(missing))
    return Settings(
        _env_file=None,
        environment="test",
        database_url="sqlite+aiosqlite:///./external-s3-test.db",
        s3_internal_endpoint=required["MEDIA_TEST_S3_INTERNAL_ENDPOINT"],
        s3_public_endpoint=required["MEDIA_TEST_S3_PUBLIC_ENDPOINT"],
        s3_access_key=required["MEDIA_TEST_S3_ACCESS_KEY"],
        s3_secret_key=required["MEDIA_TEST_S3_SECRET_KEY"],
        s3_bucket=required["MEDIA_TEST_S3_BUCKET"],
        public_base_url=required["MEDIA_TEST_S3_PUBLIC_ENDPOINT"],
    )


async def test_presign_upload_head_read_and_delete_existing_s3() -> None:
    settings = external_test_settings()
    storage = S3ObjectStorage(settings)
    prefix = os.getenv("MEDIA_TEST_S3_PREFIX", "flashmarket-media-tests").strip("/")
    key = f"{prefix}/{uuid.uuid4()}/probe.pdf"
    asset_id = str(uuid.uuid4())
    content = b"%PDF-1.4\n%%EOF\n"
    post = await storage.create_presigned_post(
        key=key,
        content_type="application/pdf",
        size=len(content),
        asset_id=asset_id,
        expires_in=60,
        inline=False,
    )
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                post.url,
                data=post.fields,
                files={"file": ("probe.pdf", content, "application/pdf")},
            )
        assert response.status_code in {200, 201, 204}, response.text
        head = await storage.head_object(key)
        assert head.size == len(content)
        assert head.metadata["asset-id"] == asset_id
        assert await storage.read_object(key, len(content)) == content
    finally:
        await storage.delete_object(key)
