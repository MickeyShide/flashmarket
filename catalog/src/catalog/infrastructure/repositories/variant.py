"""Data-access operations for product variants."""

from typing import Any, cast
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from catalog.infrastructure.models import ProductVariantModel


class VariantRepository:
    """Repository for managing ProductVariantModel instances."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, variant: ProductVariantModel) -> ProductVariantModel:
        """Persist a new product variant."""
        self._session.add(variant)
        await self._session.flush()
        return variant

    async def get_by_id(self, variant_id: UUID) -> ProductVariantModel | None:
        """Retrieve a variant by ID eagerly loading product relationship."""
        stmt = (
            select(ProductVariantModel)
            .options(selectinload(ProductVariantModel.product))
            .where(ProductVariantModel.id == variant_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_sku(self, sku: str) -> ProductVariantModel | None:
        """Retrieve a variant by SKU."""
        stmt = (
            select(ProductVariantModel)
            .options(selectinload(ProductVariantModel.product))
            .where(ProductVariantModel.sku == sku)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_product(self, product_id: UUID) -> list[ProductVariantModel]:
        """List all variants for a given product ordered by sort_order."""
        stmt = (
            select(ProductVariantModel)
            .options(selectinload(ProductVariantModel.product))
            .where(ProductVariantModel.product_id == product_id)
            .order_by(ProductVariantModel.sort_order.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, variant: ProductVariantModel) -> ProductVariantModel:
        """Flush changes to a variant model."""
        await self._session.flush()
        return variant

    async def delete(self, variant_id: UUID) -> bool:
        """Delete a variant by ID."""
        stmt = delete(ProductVariantModel).where(ProductVariantModel.id == variant_id)
        result = cast(CursorResult[Any], await self._session.execute(stmt))
        return bool(result.rowcount > 0)

    async def sku_exists(self, sku: str) -> bool:
        """Check if a SKU already exists."""
        stmt = (
            select(func.count())
            .select_from(ProductVariantModel)
            .where(ProductVariantModel.sku == sku)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one() > 0

    async def exists_by_options(
        self, product_id: UUID, size: str | None, color: str | None
    ) -> bool:
        """Check if a size+color combination exists for a product."""
        stmt = (
            select(func.count())
            .select_from(ProductVariantModel)
            .where(
                ProductVariantModel.product_id == product_id,
                ProductVariantModel.size == size,
                ProductVariantModel.color == color,
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one() > 0
