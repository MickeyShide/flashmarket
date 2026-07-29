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

DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_inventory_service(db: DbSession) -> InventoryService:
    """Build an inventory service for the current request."""
    return InventoryService(
        session=db,
        stock_repo=StockRepository(db),
        reservation_repo=ReservationRepository(db),
        outbox_repo=OutboxRepository(db),
    )


InventoryServiceDep = Annotated[InventoryService, Depends(get_inventory_service)]
