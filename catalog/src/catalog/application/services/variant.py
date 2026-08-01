"""Application service for managing product variants."""

import re
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from catalog.application.schemas import CreateVariantRequest, UpdateVariantRequest
from catalog.domain.exceptions import (
    DuplicateSKU,
    DuplicateVariantOptions,
    ProductNotFound,
    VariantNotFound,
)
from catalog.infrastructure.models import ProductVariantModel
from catalog.infrastructure.repositories.product import ProductRepository
from catalog.infrastructure.repositories.variant import VariantRepository


def slugify_simple(text: str) -> str:
    """Simple alphanumeric slugifier for SKU generation."""
    clean = re.sub(r"[^\w\s-]", "", text).strip()
    return re.sub(r"[-\s]+", "-", clean)


class VariantService:
    """Orchestrates creation, validation, and maintenance of product variants."""

    def __init__(
        self,
        session: AsyncSession,
        repo: VariantRepository,
        product_repo: ProductRepository,
    ) -> None:
        self._session = session
        self._repo = repo
        self._product_repo = product_repo

    async def generate_sku(self, product_name: str, size: str | None, color: str | None) -> str:
        """Generate a unique SKU based on product name, color, and size."""
        words = product_name.split()[:3]
        prefix_parts = [slugify_simple(w)[:3].upper() for w in words if w]
        prefix = "-".join(prefix_parts) or "ITEM"

        parts = [prefix]
        if color:
            parts.append(slugify_simple(color)[:3].upper())
        if size:
            parts.append(size.strip().upper())

        base_sku = "-".join(parts)
        candidate = base_sku
        counter = 1

        while await self._repo.sku_exists(candidate):
            counter += 1
            candidate = f"{base_sku}-{counter}"

        return candidate

    async def create_variant(
        self, product_id: UUID, data: CreateVariantRequest
    ) -> ProductVariantModel:
        """Create a new variant for a product."""
        product = await self._product_repo.get_by_id(product_id)
        if not product:
            raise ProductNotFound()

        if data.size or data.color:
            if await self._repo.exists_by_options(product_id, data.size, data.color):
                raise DuplicateVariantOptions()

        if data.sku:
            sku = data.sku.strip().upper()
            if await self._repo.sku_exists(sku):
                raise DuplicateSKU()
        else:
            sku = await self.generate_sku(product.name, data.size, data.color)

        variant = ProductVariantModel(
            product_id=product_id,
            sku=sku,
            size=data.size,
            color=data.color,
            color_hex=data.color_hex,
            material=data.material,
            weight_grams=data.weight_grams,
            price_override=data.price_override,
            is_active=data.is_active,
            sort_order=data.sort_order,
        )

        try:
            await self._repo.create(variant)
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise DuplicateSKU() from exc

        persisted = await self._repo.get_by_id(variant.id)
        if persisted is None:
            raise VariantNotFound()
        return persisted

    async def get_by_id(
        self, variant_id: UUID, product_id: UUID | None = None
    ) -> ProductVariantModel:
        """Fetch variant by ID, checking product ownership if provided."""
        variant = await self._repo.get_by_id(variant_id)
        if not variant or (product_id is not None and variant.product_id != product_id):
            raise VariantNotFound()
        return variant

    async def list_variants(self, product_id: UUID) -> list[ProductVariantModel]:
        """List all variants for a product."""
        product = await self._product_repo.get_by_id(product_id)
        if not product:
            raise ProductNotFound()
        return await self._repo.list_by_product(product_id)

    async def update_variant(
        self,
        variant_id: UUID,
        data: UpdateVariantRequest,
        product_id: UUID | None = None,
    ) -> ProductVariantModel:
        """Update fields of an existing variant."""
        variant = await self.get_by_id(variant_id, product_id=product_id)

        if data.sku is not None and data.sku.strip().upper() != variant.sku:
            new_sku = data.sku.strip().upper()
            if await self._repo.sku_exists(new_sku):
                raise DuplicateSKU()
            variant.sku = new_sku

        if data.size is not None:
            variant.size = data.size
        if data.color is not None:
            variant.color = data.color
        if data.color_hex is not None:
            variant.color_hex = data.color_hex
        if data.material is not None:
            variant.material = data.material
        if data.weight_grams is not None:
            variant.weight_grams = data.weight_grams
        if data.price_override is not None:
            variant.price_override = data.price_override
        if data.is_active is not None:
            variant.is_active = data.is_active
        if data.sort_order is not None:
            variant.sort_order = data.sort_order

        try:
            await self._repo.update(variant)
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise DuplicateSKU() from exc

        persisted = await self._repo.get_by_id(variant.id)
        if persisted is None:
            raise VariantNotFound()
        return persisted

    async def delete_variant(self, variant_id: UUID, product_id: UUID | None = None) -> None:
        """Delete a variant by ID."""
        variant = await self.get_by_id(variant_id, product_id=product_id)
        deleted = await self._repo.delete(variant.id)
        if not deleted:
            raise VariantNotFound()
        await self._session.commit()
