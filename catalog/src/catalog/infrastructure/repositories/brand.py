"""Brand persistence operations."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from catalog.infrastructure.models import BrandModel


class BrandRepository:
    """Data-access layer for product brands."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, brand: BrandModel) -> BrandModel:
        """Persist a new brand."""
        self._session.add(brand)
        await self._session.flush()
        return brand

    async def get_by_id(self, brand_id: UUID) -> BrandModel | None:
        """Fetch a brand by its primary key."""
        result = await self._session.scalars(
            select(BrandModel).where(BrandModel.id == brand_id)
        )
        return result.first()

    async def get_by_slug(self, slug: str) -> BrandModel | None:
        """Fetch a brand by its unique slug."""
        result = await self._session.scalars(
            select(BrandModel).where(BrandModel.slug == slug)
        )
        return result.first()

    async def slug_exists(self, slug: str) -> bool:
        """Check whether a brand slug is taken."""
        result = await self._session.scalar(
            select(func.count()).select_from(BrandModel).where(BrandModel.slug == slug)
        )
        return (result or 0) > 0

    async def list_all(self) -> list[BrandModel]:
        """Return all brands ordered alphabetically by name."""
        result = await self._session.scalars(
            select(BrandModel).order_by(BrandModel.name)
        )
        return list(result.all())
