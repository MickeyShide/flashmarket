"""Retry-safe cleanup of expired and deleting assets."""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from media_service.application.contracts import ObjectStorage
from media_service.domain.entities import AssetStatus
from media_service.domain.exceptions import StorageObjectNotFound, StorageUnavailable
from media_service.infrastructure.repositories import MediaAssetRepository
from media_service.observability import DELETION_QUEUE, PENDING_ASSETS


class CleanupService:
    """Process one bounded cleanup batch."""

    def __init__(
        self,
        session: AsyncSession,
        repository: MediaAssetRepository,
        storage: ObjectStorage,
    ) -> None:
        self._session = session
        self._repository = repository
        self._storage = storage

    async def run_once(self, batch_size: int) -> int:
        """Delete objects for expired sessions and requested deletions."""
        now = datetime.now(UTC)
        assets = await self._repository.cleanup_candidates(now, batch_size)
        processed = 0
        for asset in assets:
            try:
                await self._storage.delete_object(asset.object_key)
            except StorageObjectNotFound:
                pass
            except StorageUnavailable:
                continue
            if asset.status == AssetStatus.DELETING:
                asset.status = AssetStatus.DELETED
                asset.deleted_at = now
            else:
                asset.status = AssetStatus.EXPIRED
                asset.failure_code = "upload_expired"
            processed += 1
        await self._session.commit()
        counts = await self._repository.queue_counts()
        PENDING_ASSETS.set(counts.pending)
        DELETION_QUEUE.set(counts.deleting)
        return processed
