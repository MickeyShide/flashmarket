"""FastAPI dependency injection wiring."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from inventory.application.services.stock import InventoryService
from inventory.infrastructure.database import get_db
from inventory.infrastructure.repositories.stock import (
    OutboxRepository,
    ReservationRepository,
    StockRepository,
)

from functools import lru_cache
from jwt_verifier import JWTVerifier, Principal, create_auth_dependencies
from inventory.config import get_settings

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


get_optional_principal, get_current_principal, require_admin = create_auth_dependencies(get_verifier)

OptionalPrincipal = Annotated[Principal | None, Depends(get_optional_principal)]
CurrentPrincipal = Annotated[Principal, Depends(get_current_principal)]
AdminPrincipal = Annotated[Principal, Depends(require_admin)]


def get_inventory_service(db: DbSession) -> InventoryService:
    """Build an inventory service for the current request."""
    return InventoryService(
        session=db,
        stock_repo=StockRepository(db),
        reservation_repo=ReservationRepository(db),
        outbox_repo=OutboxRepository(db),
    )


InventoryServiceDep = Annotated[InventoryService, Depends(get_inventory_service)]
