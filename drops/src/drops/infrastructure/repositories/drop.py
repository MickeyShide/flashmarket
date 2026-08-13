"""Data access operations for drops and drop items."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from drops.domain.entities import DropStatus
from drops.infrastructure.models import DropItemModel, DropModel


@dataclass(frozen=True, slots=True)
class DropPage:
    """Paginated list of drops."""

    items: list[DropModel]
    total: int


class DropRepository:
    """Handles CRUD operations for DropModel and DropItemModel."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, drop: DropModel) -> DropModel:
        """Persist a new drop record."""
        self._session.add(drop)
        await self._session.flush()
        return drop

    async def get_by_id(self, drop_id: UUID) -> DropModel | None:
        """Retrieve a drop by ID with eagerly loaded items."""
        stmt = (
            select(DropModel).options(selectinload(DropModel.items)).where(DropModel.id == drop_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> DropModel | None:
        """Retrieve a drop by slug with eagerly loaded items."""
        stmt = (
            select(DropModel).options(selectinload(DropModel.items)).where(DropModel.slug == slug)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def slug_exists(self, slug: str) -> bool:
        """Check if a drop with the given slug exists."""
        stmt = select(func.count()).select_from(DropModel).where(DropModel.slug == slug)
        result = await self._session.execute(stmt)
        return result.scalar_one() > 0

    async def list_active(self) -> list[DropModel]:
        """List drops currently in ACTIVE status, ordered by starts_at."""
        stmt = (
            select(DropModel)
            .options(selectinload(DropModel.items))
            .where(DropModel.status == DropStatus.ACTIVE)
            .order_by(DropModel.starts_at.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_upcoming(self) -> list[DropModel]:
        """List drops currently in SCHEDULED status, ordered by starts_at."""
        stmt = (
            select(DropModel)
            .options(selectinload(DropModel.items))
            .where(DropModel.status == DropStatus.SCHEDULED)
            .order_by(DropModel.starts_at.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_all(self, limit: int, offset: int, status: DropStatus | None = None) -> DropPage:
        """List all drops with pagination and optional status filter."""
        count_stmt = select(func.count()).select_from(DropModel)
        stmt = select(DropModel).options(selectinload(DropModel.items))

        if status is not None:
            count_stmt = count_stmt.where(DropModel.status == status)
            stmt = stmt.where(DropModel.status == status)

        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = stmt.order_by(DropModel.starts_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        items = list(result.scalars().all())

        return DropPage(items=items, total=total)

    async def get_due_to_start(self, now: datetime) -> list[DropModel]:
        """Get SCHEDULED drops whose starts_at is in the past or now."""
        stmt = (
            select(DropModel)
            .options(selectinload(DropModel.items))
            .where(
                DropModel.status == DropStatus.SCHEDULED,
                DropModel.starts_at <= now,
            )
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_due_to_end(self, now: datetime) -> list[DropModel]:
        """Get ACTIVE drops whose ends_at is in the past or now."""
        stmt = (
            select(DropModel)
            .options(selectinload(DropModel.items))
            .where(
                DropModel.status == DropStatus.ACTIVE,
                DropModel.ends_at <= now,
            )
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, drop: DropModel) -> DropModel:
        """Flush changes to drop model."""
        await self._session.flush()
        return drop

    async def add_item(self, item: DropItemModel) -> DropItemModel:
        """Add a product item to a drop."""
        self._session.add(item)
        await self._session.flush()
        return item

    async def remove_item(self, drop_id: UUID, product_id: UUID) -> bool:
        """Remove a product item from a drop."""
        stmt = delete(DropItemModel).where(
            DropItemModel.drop_id == drop_id,
            DropItemModel.product_id == product_id,
        )
        result = await self._session.execute(stmt)
        return bool(result.rowcount > 0)
