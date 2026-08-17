from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from catalog.application.schemas import (
    CreateCategoryRequest,
    CreateProductRequest,
    CreateVariantRequest,
)
from catalog.application.services.category import CategoryService
from catalog.application.services.product import ProductService
from catalog.application.services.variant import VariantService
from catalog.domain.exceptions import DuplicateSlug, DuplicateVariantOptions
from catalog.infrastructure.repositories.category import CategoryRepository
from catalog.infrastructure.repositories.product import ProductRepository
from catalog.infrastructure.repositories.variant import VariantRepository


@pytest.mark.asyncio
async def test_duplicate_variant_with_nullable_options_rejected(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Variants with size=None and same color are rejected by unique constraint."""
    async with session_factory() as session:
        cat_repo = CategoryRepository(session)
        prod_repo = ProductRepository(session)
        var_repo = VariantRepository(session)
        cat_service = CategoryService(session, cat_repo, AsyncMock())
        prod_service = ProductService(session, prod_repo, cat_repo)
        var_service = VariantService(session, var_repo, prod_repo)

        cat = await cat_service.create_category(
            CreateCategoryRequest(name="Accessories", slug="accessories")
        )
        prod = await prod_service.create_product(
            CreateProductRequest(
                name="Silk Scarf",
                price=Decimal("3500.00"),
                category_id=cat.id,
            )
        )

        # 1. Create first variant with size=None, color="Navy"
        v1 = await var_service.create_variant(
            prod.id,
            CreateVariantRequest(size=None, color="Navy"),
        )
        assert v1.id is not None
        assert v1.size is None
        assert v1.color == "Navy"

        # 2. Attempt to create second variant with identical size=None, color="Navy" -> must raise
        with pytest.raises(DuplicateVariantOptions):
            await var_service.create_variant(
                prod.id,
                CreateVariantRequest(size=None, color="Navy"),
            )


@pytest.mark.asyncio
async def test_slug_generation_collision_limit_exhaustion() -> None:
    """When all 100 collision slug suffixes are occupied, DuplicateSlug is raised."""
    mock_prod_repo = AsyncMock(spec=ProductRepository)
    # Simulate every possible candidate slug already existing in database
    mock_prod_repo.slug_exists.return_value = True

    prod_service = ProductService(
        session=AsyncMock(spec=AsyncSession),
        product_repo=mock_prod_repo,
        category_repo=AsyncMock(spec=CategoryRepository),
    )

    with pytest.raises(DuplicateSlug):
        await prod_service.generate_unique_slug("Popular Sneaker")

    # Verify all 100 candidate checks were performed
    assert mock_prod_repo.slug_exists.call_count >= 100
