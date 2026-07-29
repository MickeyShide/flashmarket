"""Payment and outbox persistence operations."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from payments.infrastructure.database import utc_now
from payments.infrastructure.models import OutboxEventModel, PaymentModel


class PaymentRepository:
    """Data-access layer for payments."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, payment: PaymentModel) -> PaymentModel:
        """Persist a new payment."""
        self._session.add(payment)
        await self._session.flush()
        return payment

    async def get_by_id(self, payment_id: UUID) -> PaymentModel | None:
        """Fetch a payment by primary key."""
        return await self._session.get(PaymentModel, payment_id)

    async def get_by_order_id(self, order_id: UUID) -> PaymentModel | None:
        """Fetch the most recent payment for an order."""
        result = await self._session.scalars(
            select(PaymentModel)
            .where(PaymentModel.order_id == order_id)
            .order_by(PaymentModel.created_at.desc())
        )
        return result.first()

    async def count_by_user(self, user_id: UUID) -> int:
        """Return the total number of payments for a user."""
        result = await self._session.scalar(
            select(func.count(PaymentModel.id)).where(PaymentModel.user_id == user_id)
        )
        return result or 0

    async def list_by_user(
        self,
        user_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> Sequence[PaymentModel]:
        """Return a user's payments ordered by creation time."""
        result = await self._session.scalars(
            select(PaymentModel)
            .where(PaymentModel.user_id == user_id)
            .order_by(PaymentModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.all()

    async def update(self, payment: PaymentModel) -> PaymentModel:
        """Flush pending attribute changes on a payment."""
        await self._session.flush()
        return payment


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
