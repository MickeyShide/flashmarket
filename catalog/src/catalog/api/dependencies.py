"""FastAPI dependency injection wiring."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from catalog.application.services.category import CategoryService
from catalog.application.services.product import ProductService
from catalog.infrastructure.database import get_db
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


ProductServiceDep = Annotated[ProductService, Depends(get_product_service)]
CategoryServiceDep = Annotated[CategoryService, Depends(get_category_service)]
