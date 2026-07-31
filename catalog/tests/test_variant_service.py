"""Unit and integration tests for VariantService."""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from catalog.application.schemas import (
    CreateCategoryRequest,
    CreateProductRequest,
    CreateVariantRequest,
    UpdateVariantRequest,
    VariantResponse,
)
from catalog.application.services.category import CategoryService
from catalog.application.services.product import ProductService
from catalog.application.services.variant import VariantService
from catalog.domain.exceptions import (
    DuplicateSKU,
    DuplicateVariantOptions,
)
from catalog.infrastructure.repositories.category import CategoryRepository
from catalog.infrastructure.repositories.product import ProductRepository
from catalog.infrastructure.repositories.variant import VariantRepository


async def _create_test_product(session: AsyncSession):
    cat_repo = CategoryRepository(session)
    prod_repo = ProductRepository(session)
    cat_service = CategoryService(session, cat_repo)
    prod_service = ProductService(session, prod_repo, cat_repo)

    category = await cat_service.create_category(
        CreateCategoryRequest(name="Clothing", slug="clothing")
    )
    product = await prod_service.create_product(
        CreateProductRequest(
            name="Flash Hoodie",
            price=Decimal("5000.00"),
            category_id=category.id,
        )
    )
    return product


@pytest.mark.asyncio
async def test_create_variant(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        product = await _create_test_product(session)
        var_repo = VariantRepository(session)
        prod_repo = ProductRepository(session)
        service = VariantService(session, var_repo, prod_repo)

        req = CreateVariantRequest(
            sku="FSH-BLK-S",
            size="S",
            color="Black",
            price_override=Decimal("4500.00"),
        )
        variant = await service.create_variant(product.id, req)

        assert variant.id is not None
        assert variant.product_id == product.id
        assert variant.sku == "FSH-BLK-S"
        assert variant.size == "S"
        assert variant.color == "Black"
        assert variant.price_override == Decimal("4500.00")


@pytest.mark.asyncio
async def test_create_variant_auto_sku(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        product = await _create_test_product(session)
        var_repo = VariantRepository(session)
        prod_repo = ProductRepository(session)
        service = VariantService(session, var_repo, prod_repo)

        req = CreateVariantRequest(size="M", color="White")
        variant = await service.create_variant(product.id, req)

        assert variant.sku == "FLA-HOO-WHI-M"


@pytest.mark.asyncio
async def test_duplicate_sku(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        product = await _create_test_product(session)
        var_repo = VariantRepository(session)
        prod_repo = ProductRepository(session)
        service = VariantService(session, var_repo, prod_repo)

        req1 = CreateVariantRequest(sku="UNIQUE-SKU", size="S")
        await service.create_variant(product.id, req1)

        req2 = CreateVariantRequest(sku="UNIQUE-SKU", size="M")
        with pytest.raises(DuplicateSKU):
            await service.create_variant(product.id, req2)


@pytest.mark.asyncio
async def test_duplicate_size_color(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        product = await _create_test_product(session)
        var_repo = VariantRepository(session)
        prod_repo = ProductRepository(session)
        service = VariantService(session, var_repo, prod_repo)

        req1 = CreateVariantRequest(size="L", color="Red")
        await service.create_variant(product.id, req1)

        req2 = CreateVariantRequest(size="L", color="Red")
        with pytest.raises(DuplicateVariantOptions):
            await service.create_variant(product.id, req2)


@pytest.mark.asyncio
async def test_list_variants(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        product = await _create_test_product(session)
        var_repo = VariantRepository(session)
        prod_repo = ProductRepository(session)
        service = VariantService(session, var_repo, prod_repo)

        await service.create_variant(product.id, CreateVariantRequest(size="S", color="Black"))
        await service.create_variant(product.id, CreateVariantRequest(size="M", color="Black"))

        variants = await service.list_variants(product.id)
        assert len(variants) == 2


@pytest.mark.asyncio
async def test_update_variant(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        product = await _create_test_product(session)
        var_repo = VariantRepository(session)
        prod_repo = ProductRepository(session)
        service = VariantService(session, var_repo, prod_repo)

        variant = await service.create_variant(
            product.id, CreateVariantRequest(size="S", color="Blue")
        )

        updated = await service.update_variant(
            variant.id, UpdateVariantRequest(color="Navy", price_override=Decimal("6000.00"))
        )

        assert updated.color == "Navy"
        assert updated.price_override == Decimal("6000.00")


@pytest.mark.asyncio
async def test_delete_variant(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        product = await _create_test_product(session)
        var_repo = VariantRepository(session)
        prod_repo = ProductRepository(session)
        service = VariantService(session, var_repo, prod_repo)

        variant = await service.create_variant(
            product.id, CreateVariantRequest(size="XL", color="Green")
        )

        await service.delete_variant(variant.id)
        variants = await service.list_variants(product.id)
        assert len(variants) == 0


@pytest.mark.asyncio
async def test_effective_price_computation(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        product = await _create_test_product(session)
        var_repo = VariantRepository(session)
        prod_repo = ProductRepository(session)
        service = VariantService(session, var_repo, prod_repo)

        # Variant with price_override
        v1 = await service.create_variant(
            product.id, CreateVariantRequest(size="S", price_override=Decimal("4000.00"))
        )
        res1 = VariantResponse.model_validate(v1)
        assert res1.effective_price == Decimal("4000.00")

        # Variant without price_override -> uses product.price
        v2 = await service.create_variant(product.id, CreateVariantRequest(size="M"))
        res2 = VariantResponse.model_validate(v2)
        assert res2.effective_price == Decimal("5000.00")
