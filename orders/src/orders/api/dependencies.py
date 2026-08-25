"""FastAPI dependency injection wiring."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from jwt_verifier import JWTVerifier, Principal, create_auth_dependencies
from sqlalchemy.ext.asyncio import AsyncSession

from orders.application.services.order import OrderService
from orders.application.services.promocode import PromocodeService
from orders.config import get_settings
from orders.infrastructure.catalog_client import CatalogClient
from orders.infrastructure.database import get_db
from orders.infrastructure.repositories.order import OrderRepository, OutboxRepository
from orders.infrastructure.repositories.promocode import PromocodeRepository

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


@lru_cache
def get_catalog_client() -> CatalogClient | None:
    settings = get_settings()
    if not settings.catalog_base_url:
        return None
    return CatalogClient(
        base_url=settings.catalog_base_url,
        timeout_seconds=settings.catalog_timeout_seconds,
    )


get_optional_principal, get_current_principal, require_admin = create_auth_dependencies(
    get_verifier
)

OptionalPrincipal = Annotated[Principal | None, Depends(get_optional_principal)]
CurrentPrincipal = Annotated[Principal, Depends(get_current_principal)]
AdminPrincipal = Annotated[Principal, Depends(require_admin)]


def get_promocode_service(db: DbSession) -> PromocodeService:
    """Build a promocode service for the current request."""
    return PromocodeService(session=db, repo=PromocodeRepository(db))


PromocodeServiceDep = Annotated[PromocodeService, Depends(get_promocode_service)]


def get_order_service(db: DbSession) -> OrderService:
    """Build an order service for the current request."""
    promocode_service = PromocodeService(session=db, repo=PromocodeRepository(db))
    return OrderService(
        session=db,
        order_repo=OrderRepository(db),
        outbox_repo=OutboxRepository(db),
        promocode_service=promocode_service,
        catalog_client=get_catalog_client(),
    )


OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]
