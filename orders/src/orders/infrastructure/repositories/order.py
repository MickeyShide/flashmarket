"""Order and outbox persistence operations."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from orders.infrastructure.database import utc_now
from orders.infrastructure.models import OrderModel, OutboxEventModel


class OrderRepository:
    """Data-access layer for orders."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, order: OrderModel) -> OrderModel:
        """Persist a new order."""
        self._session.add(order)
        await self._session.flush()
        return order

    async def get_by_id(self, order_id: UUID) -> OrderModel | None:
        """Fetch an order by primary key."""
        return await self._session.get(OrderModel, order_id)

    async def get_by_reservation_id(self, reservation_id: UUID) -> OrderModel | None:
        """Fetch an order by reservation id."""
        result = await self._session.scalars(
            select(OrderModel).where(OrderModel.reservation_id == reservation_id)
        )
        return result.first()

    async def count_by_user(self, user_id: UUID) -> int:
        """Return the total number of orders for a user."""
        result = await self._session.scalar(
            select(func.count(OrderModel.id)).where(OrderModel.user_id == user_id)
        )
        return result or 0

    async def list_by_user(
        self,
        user_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> Sequence[OrderModel]:
        """Return a user's orders ordered by creation time."""
        result = await self._session.scalars(
            select(OrderModel)
            .where(OrderModel.user_id == user_id)
            .order_by(OrderModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.all()

    async def update(self, order: OrderModel) -> OrderModel:
        """Flush pending attribute changes on an order."""
        await self._session.flush()
        return order


class OutboxRepository:
    """Transactional outbox persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, event_type: str, payload: str) -> OutboxEventModel:
        """Persist an outbox event within the current transaction."""
        event = OutboxEventModel(event_type=event_type, payload=payload)
        self._session.add(event)
        await self._session.flush()
        return event

    async def list_pending(self, limit: int) -> Sequence[OutboxEventModel]:
        """Return pending outbox events for the relay worker."""
        result = await self._session.scalars(
            select(OutboxEventModel)
            .where(OutboxEventModel.status == "pending")
            .order_by(OutboxEventModel.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return result.all()

    async def mark_published(self, event: OutboxEventModel) -> OutboxEventModel:
        """Mark an outbox event as published."""
        event.status = "published"
        event.published_at = utc_now()
        await self._session.flush()
        return event

    async def mark_failed(self, event: OutboxEventModel) -> OutboxEventModel:
        """Mark an outbox event as failed."""
        event.status = "failed"
        event.published_at = None
        await self._session.flush()
        return event
