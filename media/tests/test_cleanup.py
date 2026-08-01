"""Cleanup worker tests."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from media_service.application.services.cleanup import CleanupService
from media_service.domain.entities import AssetStatus, Visibility
from media_service.infrastructure.models import MediaAssetModel
from media_service.infrastructure.repositories import MediaAssetRepository
from tests.conftest import FakeStorage


async def test_cleanup_expires_abandoned_upload_and_finishes_deletion(
    db_session: AsyncSession, fake_storage: FakeStorage
) -> None:
    now = datetime.now(UTC)
    expired = MediaAssetModel(
        uploader_id=uuid4(),
        purpose="review_image",
        status=AssetStatus.PENDING,
        visibility=Visibility.PUBLIC,
        bucket="test-public",
        object_key="review_image/expired.png",
        original_filename="expired.png",
        declared_content_type="image/png",
        expected_size=10,
        upload_expires_at=now - timedelta(minutes=1),
    )
    deleting = MediaAssetModel(
        uploader_id=uuid4(),
        purpose="review_image",
        status=AssetStatus.DELETING,
        visibility=Visibility.PUBLIC,
        bucket="test-public",
        object_key="review_image/delete.png",
        original_filename="delete.png",
        declared_content_type="image/png",
        expected_size=10,
        upload_expires_at=now + timedelta(minutes=1),
        delete_requested_at=now,
    )
    db_session.add_all([expired, deleting])
    await db_session.commit()
    fake_storage.objects[expired.object_key] = (b"x" * 10, "image/png", {})
    fake_storage.objects[deleting.object_key] = (b"x" * 10, "image/png", {})

    processed = await CleanupService(
        db_session, MediaAssetRepository(db_session), fake_storage
    ).run_once(10)

    assert processed == 2
    assert expired.status == AssetStatus.EXPIRED
    assert deleting.status == AssetStatus.DELETED
    assert not fake_storage.objects
