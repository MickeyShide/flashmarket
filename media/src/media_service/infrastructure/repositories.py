"""SQLAlchemy repository for media assets."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from media_service.domain.entities import AssetStatus
from media_service.infrastructure.models import MediaAssetModel


@dataclass(frozen=True, slots=True)
class AssetPage:
    items: list[MediaAssetModel]
    total: int


@dataclass(frozen=True, slots=True)
class UserUsage:
    pending: int
    ready: int
    ready_bytes: int


@dataclass(frozen=True, slots=True)
class QueueCounts:
    pending: int
    deleting: int


class MediaAssetRepository:
    """Persistence operations used by application services."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, asset: MediaAssetModel) -> None:
        self._session.add(asset)
        await self._session.flush()

    async def get(self, asset_id: UUID, *, for_update: bool = False) -> MediaAssetModel | None:
        statement = select(MediaAssetModel).where(MediaAssetModel.id == asset_id)
        if for_update:
            statement = statement.with_for_update()
        return (await self._session.execute(statement)).scalar_one_or_none()

    async def user_usage(self, uploader_id: UUID) -> UserUsage:
        pending = await self._session.scalar(
            select(func.count())
            .select_from(MediaAssetModel)
            .where(
                MediaAssetModel.uploader_id == uploader_id,
                MediaAssetModel.status.in_([AssetStatus.PENDING, AssetStatus.VERIFYING]),
            )
        )
        ready, ready_bytes = (
            await self._session.execute(
                select(func.count(), func.coalesce(func.sum(MediaAssetModel.actual_size), 0)).where(
                    MediaAssetModel.uploader_id == uploader_id,
                    MediaAssetModel.status == AssetStatus.READY,
                )
            )
        ).one()
        return UserUsage(int(pending or 0), int(ready or 0), int(ready_bytes or 0))

    async def list_assets(
        self,
        *,
        uploader_id: UUID | None = None,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        purpose: str | None = None,
        status: AssetStatus | None = None,
        limit: int,
        offset: int,
    ) -> AssetPage:
        filters = []
        if uploader_id is not None:
            filters.append(MediaAssetModel.uploader_id == uploader_id)
        if entity_type is not None:
            filters.append(MediaAssetModel.entity_type == entity_type)
        if entity_id is not None:
            filters.append(MediaAssetModel.entity_id == entity_id)
        if purpose is not None:
            filters.append(MediaAssetModel.purpose == purpose)
        if status is not None:
            filters.append(MediaAssetModel.status == status)
        total = await self._session.scalar(
            select(func.count()).select_from(MediaAssetModel).where(*filters)
        )
        result = await self._session.scalars(
            select(MediaAssetModel)
            .where(*filters)
            .order_by(MediaAssetModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return AssetPage(list(result.all()), int(total or 0))

    async def cleanup_candidates(self, now: datetime, limit: int) -> list[MediaAssetModel]:
        statement = (
            select(MediaAssetModel)
            .where(
                (MediaAssetModel.status == AssetStatus.DELETING)
                | (
                    MediaAssetModel.status.in_([AssetStatus.PENDING, AssetStatus.VERIFYING])
                    & (MediaAssetModel.upload_expires_at <= now)
                )
            )
            .order_by(MediaAssetModel.updated_at)
            .with_for_update(skip_locked=True)
            .limit(limit)
        )
        return list((await self._session.scalars(statement)).all())

    async def queue_counts(self) -> QueueCounts:
        """Return current queue depths for operational metrics."""
        pending = await self._session.scalar(
            select(func.count())
            .select_from(MediaAssetModel)
            .where(MediaAssetModel.status.in_([AssetStatus.PENDING, AssetStatus.VERIFYING]))
        )
        deleting = await self._session.scalar(
            select(func.count())
            .select_from(MediaAssetModel)
            .where(MediaAssetModel.status == AssetStatus.DELETING)
        )
        return QueueCounts(int(pending or 0), int(deleting or 0))
