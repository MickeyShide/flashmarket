"""Stock and reservation persistence operations."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from inventory.domain.entities import ReservationStatus
from inventory.infrastructure.models import OutboxEventModel, ReservationModel, StockModel


class StockRepository:
    """Data-access layer for product stock."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, stock: StockModel) -> StockModel:
        """Persist a new stock record."""
        self._session.add(stock)
        await self._session.flush()
        return stock

    async def get_by_id(self, stock_id: UUID) -> StockModel | None:
        """Fetch a stock record by primary key."""
        return await self._session.get(StockModel, stock_id)

    async def get_by_product_and_variant(
        self, product_id: UUID, variant_id: UUID | None = None
    ) -> StockModel | None:
        """Fetch a stock record by product id and variant id."""
        stmt = select(StockModel).where(StockModel.product_id == product_id)
        if variant_id is not None:
            stmt = stmt.where(StockModel.variant_id == variant_id)
        else:
            stmt = stmt.where(StockModel.variant_id.is_(None))
        result = await self._session.scalars(stmt)
        return result.first()

    async def get_by_product_and_variant_for_update(
        self, product_id: UUID, variant_id: UUID | None = None
    ) -> StockModel | None:
        """Lock a stock row for atomic reservation updates."""
        stmt = select(StockModel).where(StockModel.product_id == product_id).with_for_update()
        if variant_id is not None:
            stmt = stmt.where(StockModel.variant_id == variant_id)
        else:
            stmt = stmt.where(StockModel.variant_id.is_(None))
        result = await self._session.scalars(stmt)
        return result.first()

    async def get_by_product_id(self, product_id: UUID) -> StockModel | None:
        """Fetch a stock record by product id."""
        return await self.get_by_product_and_variant(product_id, None)

    async def get_by_product_id_for_update(self, product_id: UUID) -> StockModel | None:
        """Lock a stock row for atomic reservation updates."""
        return await self.get_by_product_and_variant_for_update(product_id, None)

    async def update(self, stock: StockModel) -> StockModel:
        """Flush pending attribute changes on a stock record."""
        await self._session.flush()
        return stock


class ReservationRepository:
    """Data-access layer for reservations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, reservation: ReservationModel) -> ReservationModel:
        """Persist a new reservation."""
        self._session.add(reservation)
        await self._session.flush()
        return reservation

    async def get_by_id(self, reservation_id: UUID) -> ReservationModel | None:
        """Fetch a reservation by primary key."""
        return await self._session.get(ReservationModel, reservation_id)

    async def get_by_order_id(self, order_id: UUID) -> ReservationModel | None:
        """Fetch the active reservation bound to an order."""
        result = await self._session.scalars(
            select(ReservationModel).where(
                ReservationModel.order_id == order_id,
                ReservationModel.status == ReservationStatus.RESERVED,
            )
        )
        return result.first()

    async def list_expired(self, before: datetime) -> Sequence[ReservationModel]:
        """Return reserved reservations that have expired."""
        result = await self._session.scalars(
            select(ReservationModel)
            .where(
                ReservationModel.status == ReservationStatus.RESERVED,
                ReservationModel.expires_at <= before,
            )
            .order_by(ReservationModel.expires_at)
        )
        return result.all()

    async def update(self, reservation: ReservationModel) -> ReservationModel:
        """Flush pending attribute changes on a reservation."""
        await self._session.flush()
        return reservation


class OutboxRepository:
    """Transactional outbox persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        event_type: str,
        payload: str,
    ) -> OutboxEventModel:
        """Persist an outbox event within the current transaction."""
        event = OutboxEventModel(event_type=event_type, payload=payload)
        self._session.add(event)
        await self._session.flush()
        return event

    async def list_pending(
        self,
        limit: int,
    ) -> Sequence[OutboxEventModel]:
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
        event.published_at = datetime.now(UTC)
        await self._session.flush()
        return event

    async def mark_failed(self, event: OutboxEventModel, error: str) -> OutboxEventModel:
        """Mark an outbox event as failed and keep it for retry."""
        event.status = "failed"
        event.published_at = None
        await self._session.flush()
        return event
