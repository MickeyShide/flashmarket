"""Inventory application service."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from inventory.application.schemas import (
    CommitRequest,
    ReleaseRequest,
    ReserveRequest,
    StockCreateRequest,
    StockUpdateRequest,
)
from inventory.config import get_settings
from inventory.domain.entities import InventoryEventType, ReservationStatus
from inventory.domain.exceptions import (
    InvalidReservationState,
    OutOfStock,
    ReservationNotFound,
    StockNotFound,
)
from inventory.infrastructure.database import utc_now
from inventory.infrastructure.models import ReservationModel, StockModel
from inventory.infrastructure.repositories.stock import (
    OutboxRepository,
    ReservationRepository,
    StockRepository,
)


class InventoryService:
    """Orchestrates stock reservation, commitment and release."""

    def __init__(
        self,
        session: AsyncSession,
        stock_repo: StockRepository,
        reservation_repo: ReservationRepository,
        outbox_repo: OutboxRepository,
    ) -> None:
        self._session = session
        self._stock_repo = stock_repo
        self._reservation_repo = reservation_repo
        self._outbox_repo = outbox_repo

    async def create_stock(self, data: StockCreateRequest) -> StockModel:
        """Initialize stock for a product or variant."""
        existing = await self._stock_repo.get_by_product_and_variant(data.product_id, data.variant_id)
        if existing is not None:
            existing.total = data.total
            existing.available = data.total
            await self._stock_repo.update(existing)
            await self._session.commit()
            await self._session.refresh(existing)
            return existing

        stock = StockModel(
            product_id=data.product_id,
            variant_id=data.variant_id,
            total=data.total,
            available=data.total,
        )
        await self._stock_repo.create(stock)
        await self._session.commit()
        await self._session.refresh(stock)
        return stock

    async def update_total(
        self, product_id: UUID, data: StockUpdateRequest, variant_id: UUID | None = None
    ) -> StockModel:
        """Change the total stock of a product or variant, preserving sold units."""
        stock = await self._stock_repo.get_by_product_and_variant_for_update(product_id, variant_id)
        if stock is None:
            raise StockNotFound

        reserved_plus_sold = stock.reserved + stock.sold
        if data.total < reserved_plus_sold:
            raise OutOfStock(f"Cannot reduce total below reserved + sold ({reserved_plus_sold})")

        stock.total = data.total
        stock.available = data.total - reserved_plus_sold
        await self._stock_repo.update(stock)
        await self._session.commit()
        await self._session.refresh(stock)
        return stock

    async def get_stock(self, product_id: UUID, variant_id: UUID | None = None) -> StockModel:
        """Return stock for a product or variant."""
        stock = await self._stock_repo.get_by_product_and_variant(product_id, variant_id)
        if stock is None:
            raise StockNotFound
        return stock

    async def reserve(
        self,
        product_id: UUID,
        data: ReserveRequest,
    ) -> ReservationModel:
        """Atomically reserve stock for a user."""
        stock = await self._stock_repo.get_by_product_and_variant_for_update(
            product_id, data.variant_id
        )
        if stock is None:
            raise StockNotFound

        if stock.available < data.quantity:
            raise OutOfStock

        stock.available -= data.quantity
        stock.reserved += data.quantity
        await self._stock_repo.update(stock)

        settings = get_settings()
        expires_at = utc_now() + timedelta(seconds=settings.reservation_ttl_seconds)

        reservation = ReservationModel(
            stock_id=stock.id,
            user_id=data.user_id,
            order_id=data.order_id,
            quantity=data.quantity,
            status=ReservationStatus.RESERVED,
            expires_at=expires_at,
        )
        await self._reservation_repo.create(reservation)

        payload = {
            "reservation_id": str(reservation.id),
            "user_id": str(data.user_id),
            "product_id": str(product_id),
            "variant_id": str(stock.variant_id) if stock.variant_id else None,
            "quantity": data.quantity,
            "order_id": str(data.order_id) if data.order_id else None,
            "expires_at": reservation.expires_at.isoformat(),
        }
        await self._outbox_repo.add(
            InventoryEventType.INVENTORY_RESERVED,
            json.dumps(payload, separators=(",", ":")),
        )

        await self._session.commit()
        await self._session.refresh(reservation)
        await self._session.refresh(stock)
        return reservation

    async def commit(self, product_id: UUID, data: CommitRequest) -> ReservationModel:
        """Convert a reservation into a sale."""
        stock = await self._stock_repo.get_by_product_id_for_update(product_id)
        if stock is None:
            raise StockNotFound

        reservation = await self._reservation_repo.get_by_order_id(data.order_id)
        if reservation is None or reservation.stock_id != stock.id:
            raise ReservationNotFound

        if reservation.status != ReservationStatus.RESERVED:
            raise InvalidReservationState("Reservation is not active")

        reservation.status = ReservationStatus.COMMITTED
        stock.reserved -= reservation.quantity
        stock.sold += reservation.quantity

        await self._reservation_repo.update(reservation)
        await self._stock_repo.update(stock)

        payload = {
            "reservation_id": str(reservation.id),
            "product_id": str(product_id),
            "order_id": str(data.order_id),
            "quantity": reservation.quantity,
        }
        await self._outbox_repo.add(
            InventoryEventType.INVENTORY_COMMITTED,
            json.dumps(payload, separators=(",", ":")),
        )

        await self._session.commit()
        await self._session.refresh(reservation)
        return reservation

    async def release(self, product_id: UUID, data: ReleaseRequest) -> ReservationModel:
        """Release a reservation and return stock to available."""
        stock = await self._stock_repo.get_by_product_id_for_update(product_id)
        if stock is None:
            raise StockNotFound

        reservation = await self._reservation_repo.get_by_order_id(data.order_id)
        if reservation is None or reservation.stock_id != stock.id:
            raise ReservationNotFound

        if reservation.status != ReservationStatus.RESERVED:
            raise InvalidReservationState("Reservation is not active")

        reservation.status = ReservationStatus.RELEASED
        stock.reserved -= reservation.quantity
        stock.available += reservation.quantity

        await self._reservation_repo.update(reservation)
        await self._stock_repo.update(stock)

        payload = {
            "reservation_id": str(reservation.id),
            "product_id": str(product_id),
            "order_id": str(data.order_id),
            "quantity": reservation.quantity,
            "reason": "manual_release",
        }
        await self._outbox_repo.add(
            InventoryEventType.RESERVATION_RELEASED,
            json.dumps(payload, separators=(",", ":")),
        )

        await self._session.commit()
        await self._session.refresh(reservation)
        return reservation

    async def expire_reservations(self, batch_size: int = 100) -> int:
        """Release all expired reservations and return the count."""
        now = utc_now()
        expired = await self._reservation_repo.list_expired(now)
        count = 0
        for reservation in expired[:batch_size]:
            stock = await self._stock_repo.get_by_id(reservation.stock_id)
            if stock is None:
                continue

            reservation.status = ReservationStatus.EXPIRED
            stock.reserved -= reservation.quantity
            stock.available += reservation.quantity
            await self._reservation_repo.update(reservation)
            await self._stock_repo.update(stock)

            payload = {
                "reservation_id": str(reservation.id),
                "product_id": str(stock.product_id),
                "order_id": str(reservation.order_id) if reservation.order_id else None,
                "quantity": reservation.quantity,
                "reason": "expired",
            }
            await self._outbox_repo.add(
                InventoryEventType.RESERVATION_RELEASED,
                json.dumps(payload, separators=(",", ":")),
            )
            count += 1

        if count:
            await self._session.commit()
        return count
