"""FastAPI dependency injection wiring."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from catalog.application.services.brand import BrandService
from catalog.application.services.category import CategoryService
from catalog.application.services.product import ProductService
from catalog.infrastructure.database import get_db
from catalog.infrastructure.repositories.brand import BrandRepository
from catalog.infrastructure.repositories.category import CategoryRepository
from catalog.infrastructure.repositories.product import ProductRepository

DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_product_service(db: DbSession) -> ProductService:
    """Build a product service for the current request."""
    product_repo = ProductRepository(db)
    category_repo = CategoryRepository(db)
    return ProductService(session=db, product_repo=product_repo, category_repo=category_repo)


def get_category_service(db: DbSession) -> CategoryService:
    """Build a category service for the current request."""
    category_repo = CategoryRepository(db)
    return CategoryService(session=db, category_repo=category_repo)


def get_brand_service(db: DbSession) -> BrandService:
    """Build a brand service for the current request."""
    brand_repo = BrandRepository(db)
    return BrandService(session=db, brand_repo=brand_repo)


def get_variant_service(db: DbSession) -> VariantService:
    """Build a variant service for the current request."""
    variant_repo = VariantRepository(db)
    product_repo = ProductRepository(db)
    return VariantService(session=db, repo=variant_repo, product_repo=product_repo)


ProductServiceDep = Annotated[ProductService, Depends(get_product_service)]
CategoryServiceDep = Annotated[CategoryService, Depends(get_category_service)]
BrandServiceDep = Annotated[BrandService, Depends(get_brand_service)]
VariantServiceDep = Annotated[VariantService, Depends(get_variant_service)]

