"""Category persistence operations."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from catalog.infrastructure.models import CategoryModel


class CategoryRepository:
    """Data-access layer for categories."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, category: CategoryModel) -> CategoryModel:
        """Persist a new category."""
        self._session.add(category)
        await self._session.flush()
        return category

    async def get_by_id(self, category_id: UUID) -> CategoryModel | None:
        """Fetch a single category by primary key."""
        return await self._session.get(CategoryModel, category_id)

    async def slug_exists(self, slug: str) -> bool:
        """Check whether a category slug is already taken."""
        result = await self._session.scalar(
            select(func.count()).select_from(CategoryModel).where(CategoryModel.slug == slug)
        )
        return (result or 0) > 0

    async def list_all(self) -> list[CategoryModel]:
        """Return all categories in deterministic order for tree construction."""
        result = await self._session.scalars(select(CategoryModel).order_by(CategoryModel.name))
        return list(result.all())
