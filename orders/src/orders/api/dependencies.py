"""FastAPI dependency injection wiring."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from orders.application.services.order import OrderService
from orders.infrastructure.database import get_db
from orders.infrastructure.repositories.order import OrderRepository, OutboxRepository

DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_order_service(db: DbSession) -> OrderService:
    """Build an order service for the current request."""
    return OrderService(
        session=db,
        order_repo=OrderRepository(db),
        outbox_repo=OutboxRepository(db),
    )


OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]
