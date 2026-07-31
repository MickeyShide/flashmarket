"""FastAPI dependency injection wiring."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from orders.application.services.order import OrderService
from orders.application.services.promocode import PromocodeService
from orders.infrastructure.database import get_db
from orders.infrastructure.repositories.order import OrderRepository, OutboxRepository
from orders.infrastructure.repositories.promocode import PromocodeRepository

DbSession = Annotated[AsyncSession, Depends(get_db)]


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
    )


OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]
