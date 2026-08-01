"""Application service for flash-sale drop management."""

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from drops.application.schemas import (
    AddDropItemRequest,
    CreateDropRequest,
    DropListParams,
    UpdateDropRequest,
)
from drops.domain.entities import DropEventType, DropStatus
from drops.domain.exceptions import (
    DropNotFound,
    DropTimeConflict,
    DuplicateDropSlug,
    InvalidDropState,
    ProductAlreadyInDrop,
)
from drops.infrastructure.database import utc_now
from drops.infrastructure.models import DropItemModel, DropModel
from drops.infrastructure.repositories.drop import DropPage, DropRepository
from drops.infrastructure.repositories.outbox import OutboxRepository


class DropService:
    """Orchestrates drop domain operations, state transitions, and outbox event creation."""

    def __init__(
        self,
        session: AsyncSession,
        repo: DropRepository,
        outbox_repo: OutboxRepository,
    ) -> None:
        self._session = session
        self._repo = repo
        self._outbox_repo = outbox_repo

    async def create_drop(self, data: CreateDropRequest) -> DropModel:
        """Create a new drop in DRAFT status."""
        if await self._repo.slug_exists(data.slug):
            raise DuplicateDropSlug()

        if data.starts_at <= utc_now():
            raise DropTimeConflict("starts_at must be in the future")

        drop = DropModel(
            name=data.name,
            slug=data.slug,
            description=data.description,
            cover_image=data.cover_image,
            status=DropStatus.DRAFT,
            starts_at=data.starts_at,
            ends_at=data.ends_at,
            max_per_user=data.max_per_user,
            payment_timeout_seconds=data.payment_timeout_seconds,
        )

        try:
            await self._repo.create(drop)
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise DuplicateDropSlug() from exc

        fetched = await self._repo.get_by_id(drop.id)
        assert fetched is not None
        return fetched

    async def update_drop(self, drop_id: UUID, data: UpdateDropRequest) -> DropModel:
        """Update fields of an existing drop."""
        drop = await self._repo.get_by_id(drop_id)
        if not drop:
            raise DropNotFound()

        if drop.status not in (DropStatus.DRAFT, DropStatus.SCHEDULED):
            raise InvalidDropState("Cannot update drop that is active, ended, or cancelled")

        if data.slug is not None and data.slug != drop.slug:
            if await self._repo.slug_exists(data.slug):
                raise DuplicateDropSlug()
            drop.slug = data.slug

        if data.name is not None:
            drop.name = data.name
        if data.description is not None:
            drop.description = data.description
        if data.cover_image is not None:
            drop.cover_image = data.cover_image
        if data.max_per_user is not None:
            drop.max_per_user = data.max_per_user
        if data.payment_timeout_seconds is not None:
            drop.payment_timeout_seconds = data.payment_timeout_seconds

        new_starts = data.starts_at or drop.starts_at
        new_ends = data.ends_at or drop.ends_at
        if new_ends <= new_starts:
            raise DropTimeConflict("ends_at must be after starts_at")

        drop.starts_at = new_starts
        drop.ends_at = new_ends

        try:
            await self._repo.update(drop)
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise DuplicateDropSlug() from exc

        fetched = await self._repo.get_by_id(drop.id)
        assert fetched is not None
        return fetched

    async def schedule_drop(self, drop_id: UUID) -> DropModel:
        """Transition drop from DRAFT to SCHEDULED."""
        drop = await self._repo.get_by_id(drop_id)
        if not drop:
            raise DropNotFound()

        if drop.status != DropStatus.DRAFT:
            raise InvalidDropState("Drop must be in DRAFT status to be scheduled")

        drop.status = DropStatus.SCHEDULED
        await self._outbox_repo.create_event(
            DropEventType.DROP_SCHEDULED,
            {
                "drop_id": str(drop.id),
                "name": drop.name,
                "slug": drop.slug,
                "starts_at": drop.starts_at.isoformat(),
                "ends_at": drop.ends_at.isoformat(),
            },
        )
        await self._session.commit()
        return drop

    async def start_drop(self, drop_id: UUID) -> DropModel:
        """Transition drop from SCHEDULED to ACTIVE."""
        drop = await self._repo.get_by_id(drop_id)
        if not drop:
            raise DropNotFound()

        if drop.status != DropStatus.SCHEDULED:
            raise InvalidDropState("Drop must be in SCHEDULED status to start")

        drop.status = DropStatus.ACTIVE
        await self._outbox_repo.create_event(
            DropEventType.DROP_STARTED,
            {
                "drop_id": str(drop.id),
                "name": drop.name,
                "slug": drop.slug,
                "product_ids": [str(item.product_id) for item in drop.items],
                "max_per_user": drop.max_per_user,
            },
        )
        await self._session.commit()
        return drop

    async def end_drop(self, drop_id: UUID) -> DropModel:
        """Transition drop from ACTIVE to ENDED."""
        drop = await self._repo.get_by_id(drop_id)
        if not drop:
            raise DropNotFound()

        if drop.status != DropStatus.ACTIVE:
            raise InvalidDropState("Drop must be in ACTIVE status to end")

        drop.status = DropStatus.ENDED
        await self._outbox_repo.create_event(
            DropEventType.DROP_ENDED,
            {
                "drop_id": str(drop.id),
                "slug": drop.slug,
            },
        )
        await self._session.commit()
        return drop

    async def cancel_drop(self, drop_id: UUID) -> DropModel:
        """Cancel a drop from DRAFT, SCHEDULED, or ACTIVE status."""
        drop = await self._repo.get_by_id(drop_id)
        if not drop:
            raise DropNotFound()

        if drop.status not in (DropStatus.DRAFT, DropStatus.SCHEDULED, DropStatus.ACTIVE):
            raise InvalidDropState("Cannot cancel drop in current status")

        drop.status = DropStatus.CANCELLED
        await self._outbox_repo.create_event(
            DropEventType.DROP_CANCELLED,
            {
                "drop_id": str(drop.id),
                "slug": drop.slug,
            },
        )
        await self._session.commit()
        return drop

    async def add_item(self, drop_id: UUID, data: AddDropItemRequest) -> DropItemModel:
        """Add a product item to a drop."""
        drop = await self._repo.get_by_id(drop_id)
        if not drop:
            raise DropNotFound()

        if drop.status not in (DropStatus.DRAFT, DropStatus.SCHEDULED):
            raise InvalidDropState("Items can only be added to DRAFT or SCHEDULED drops")

        item = DropItemModel(
            drop_id=drop_id,
            product_id=data.product_id,
            sort_order=data.sort_order,
        )

        try:
            await self._repo.add_item(item)
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise ProductAlreadyInDrop() from exc

        return item

    async def remove_item(self, drop_id: UUID, product_id: UUID) -> None:
        """Remove a product item from a drop."""
        drop = await self._repo.get_by_id(drop_id)
        if not drop:
            raise DropNotFound()

        if drop.status not in (DropStatus.DRAFT, DropStatus.SCHEDULED):
            raise InvalidDropState("Items can only be removed from DRAFT or SCHEDULED drops")

        removed = await self._repo.remove_item(drop_id, product_id)
        if not removed:
            raise DropNotFound("Product item not found in drop")

        await self._session.commit()

    async def list_active(self) -> list[DropModel]:
        """Fetch all active drops."""
        return await self._repo.list_active()

    async def list_upcoming(self) -> list[DropModel]:
        """Fetch all upcoming (scheduled) drops."""
        return await self._repo.list_upcoming()

    async def list_all(self, params: DropListParams) -> DropPage:
        """Fetch all drops with pagination and optional filter."""
        return await self._repo.list_all(params.limit, params.offset, params.status)

    async def get_by_slug(self, slug: str) -> DropModel:
        """Fetch drop by slug (public endpoint filter)."""
        drop = await self._repo.get_by_slug(slug)
        if not drop:
            raise DropNotFound()
        return drop

    async def get_by_id(self, drop_id: UUID) -> DropModel:
        """Fetch drop by ID."""
        drop = await self._repo.get_by_id(drop_id)
        if not drop:
            raise DropNotFound()
        return drop
