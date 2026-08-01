"""FastAPI dependency injection wiring."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from jwt_verifier import JWTVerifier, Principal, create_auth_dependencies
from sqlalchemy.ext.asyncio import AsyncSession

from catalog.application.contracts import CategoryTreeCache
from catalog.application.services.brand import BrandService
from catalog.application.services.category import CategoryService
from catalog.application.services.product import ProductService
from catalog.application.services.variant import VariantService
from catalog.config import get_settings
from catalog.infrastructure.category_cache import category_tree_cache
from catalog.infrastructure.database import get_db
from catalog.infrastructure.repositories.brand import BrandRepository
from catalog.infrastructure.repositories.category import CategoryRepository
from catalog.infrastructure.repositories.product import ProductRepository
from catalog.infrastructure.repositories.variant import VariantRepository

DbSession = Annotated[AsyncSession, Depends(get_db)]


@lru_cache
def get_verifier() -> JWTVerifier:
    settings = get_settings()
    return JWTVerifier(
        public_key_dir=settings.jwt_public_key_dir,
        algorithm=settings.jwt_algorithm,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )


get_optional_principal, get_current_principal, require_admin = create_auth_dependencies(
    get_verifier
)

OptionalPrincipal = Annotated[Principal | None, Depends(get_optional_principal)]
CurrentPrincipal = Annotated[Principal, Depends(get_current_principal)]
AdminPrincipal = Annotated[Principal, Depends(require_admin)]


def get_category_tree_cache() -> CategoryTreeCache:
    """Return the process-wide optional category cache."""
    return category_tree_cache


CategoryTreeCacheDep = Annotated[CategoryTreeCache, Depends(get_category_tree_cache)]


def get_product_service(db: DbSession) -> ProductService:
    """Build a product service for the current request."""
    product_repo = ProductRepository(db)
    category_repo = CategoryRepository(db)
    return ProductService(session=db, product_repo=product_repo, category_repo=category_repo)


def get_category_service(
    db: DbSession,
    category_cache: CategoryTreeCacheDep,
) -> CategoryService:
    """Build a category service for the current request."""
    category_repo = CategoryRepository(db)
    return CategoryService(
        session=db,
        category_repo=category_repo,
        category_cache=category_cache,
    )


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
