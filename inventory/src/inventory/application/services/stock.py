"""Inventory application service."""

from __future__ import annotations

import json
from datetime import timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from inventory.application.contracts import StockCache
from inventory.application.schemas import (
    CommitRequest,
    ReleaseRequest,
    ReserveRequest,
    StockCreateRequest,
    StockResponse,
    StockUpdateRequest,
)
from inventory.config import get_settings
from inventory.domain.entities import InventoryEventType, ReservationStatus
from inventory.domain.exceptions import (
    DropPurchaseDenied,
    InvalidReservationState,
    OutOfStock,
    ReservationNotFound,
    StockNotFound,
)
from inventory.infrastructure.database import utc_now
from inventory.infrastructure.drop_client import DropClient
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
        stock_cache: StockCache,
        drop_client: DropClient | None = None,
    ) -> None:
        self._session = session
        self._stock_repo = stock_repo
        self._reservation_repo = reservation_repo
        self._outbox_repo = outbox_repo
        self._stock_cache = stock_cache
        self._drop_client = drop_client

    async def _cache_stock(self, stock: StockModel) -> StockResponse:
        """Store and return the public snapshot of a committed stock row."""
        snapshot = StockResponse.model_validate(stock)
        await self._stock_cache.store_stock(snapshot, stock.revision)
        return snapshot

    async def create_stock(self, data: StockCreateRequest) -> StockModel:
        """Initialize stock for a product or variant."""
        variant_id = getattr(data, "variant_id", None)
        existing = await self._stock_repo.get_by_product_and_variant_for_update(
            data.product_id,
            variant_id,
        )
        if existing is not None:
            reserved_plus_sold = existing.reserved + existing.sold
            if data.total < reserved_plus_sold:
                raise OutOfStock(f"Cannot reset total below reserved + sold ({reserved_plus_sold})")
            existing.total = data.total
            existing.available = data.total - reserved_plus_sold
            existing.revision += 1
            await self._stock_repo.update(existing)
            await self._session.commit()
            await self._session.refresh(existing)
            await self._cache_stock(existing)
            return existing

        stock = StockModel(
            product_id=data.product_id,
            variant_id=data.variant_id,
            total=data.total,
            available=data.total,
            revision=1,
        )
        await self._stock_repo.create(stock)
        await self._session.commit()
        await self._session.refresh(stock)
        await self._cache_stock(stock)
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
        stock.revision += 1
        await self._stock_repo.update(stock)
        await self._session.commit()
        await self._session.refresh(stock)
        await self._cache_stock(stock)
        return stock

    async def get_stock(
        self,
        product_id: UUID,
        variant_id: UUID | None = None,
    ) -> StockResponse:
        """Return stock for a product or variant."""
        cached = await self._stock_cache.get_stock(product_id, variant_id)
        if cached is not None:
            return cached

        stock = await self._stock_repo.get_by_product_and_variant(product_id, variant_id)
        if stock is None:
            raise StockNotFound
        return await self._cache_stock(stock)

    async def reserve(
        self,
        product_id: UUID,
        data: ReserveRequest,
    ) -> ReservationModel:
        """Atomically reserve stock for a user."""
        ttl_seconds = get_settings().reservation_ttl_seconds
        if data.drop_id is not None:
            if self._drop_client is None:
                raise DropPurchaseDenied("Drop purchase is unavailable")
            policy = await self._drop_client.get_policy(data.drop_id)
            if policy.status != "ACTIVE":
                raise DropPurchaseDenied("Drop is not active")
            if product_id not in policy.product_ids:
                raise DropPurchaseDenied("Product does not belong to this Drop")
            await self._reservation_repo.lock_drop_limit(data.user_id, data.drop_id)
            already_reserved = await self._reservation_repo.active_drop_quantity(
                data.user_id, data.drop_id, utc_now()
            )
            if already_reserved + data.quantity > policy.max_per_user:
                raise DropPurchaseDenied(f"Drop limit is {policy.max_per_user} item(s) per user")
            ttl_seconds = policy.payment_timeout_seconds

        stock = await self._stock_repo.get_by_product_and_variant_for_update(
            product_id, data.variant_id
        )
        if stock is None:
            raise StockNotFound

        if stock.available < data.quantity:
            raise OutOfStock

        stock.available -= data.quantity
        stock.reserved += data.quantity
        stock.revision += 1
        await self._stock_repo.update(stock)

        expires_at = utc_now() + timedelta(seconds=ttl_seconds)

        reservation = ReservationModel(
            stock_id=stock.id,
            user_id=data.user_id,
            order_id=data.order_id,
            drop_id=data.drop_id,
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
            "drop_id": str(data.drop_id) if data.drop_id else None,
        }
        await self._outbox_repo.add(
            InventoryEventType.INVENTORY_RESERVED,
            json.dumps(payload, separators=(",", ":")),
        )

        await self._session.commit()
        await self._session.refresh(reservation)
        await self._session.refresh(stock)
        await self._cache_stock(stock)
        return reservation

    async def commit(self, product_id: UUID, data: CommitRequest) -> ReservationModel:
        """Convert a reservation into a sale."""
        reservation = await self._reservation_repo.get_by_order_id(data.order_id)
        if reservation is None:
            raise ReservationNotFound

        stock = await self._stock_repo.get_by_id_for_update(reservation.stock_id)
        if stock is None:
            raise StockNotFound

        if reservation.status != ReservationStatus.RESERVED:
            raise InvalidReservationState("Reservation is not active")

        reservation.status = ReservationStatus.COMMITTED
        stock.reserved -= reservation.quantity
        stock.sold += reservation.quantity
        stock.revision += 1

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
        await self._session.refresh(stock)
        await self._cache_stock(stock)
        return reservation

    async def release(self, product_id: UUID, data: ReleaseRequest) -> ReservationModel:
        """Release a reservation and return stock to available."""
        reservation = (
            await self._reservation_repo.get_by_id(data.reservation_id)
            if data.reservation_id is not None
            else await self._reservation_repo.get_by_order_id(data.order_id)  # type: ignore[arg-type]
        )
        if reservation is None:
            raise ReservationNotFound

        stock = await self._stock_repo.get_by_id_for_update(reservation.stock_id)
        if stock is None:
            raise StockNotFound

        if reservation.status != ReservationStatus.RESERVED:
            raise InvalidReservationState("Reservation is not active")

        reservation.status = ReservationStatus.RELEASED
        stock.reserved -= reservation.quantity
        stock.available += reservation.quantity
        stock.revision += 1

        await self._reservation_repo.update(reservation)
        await self._stock_repo.update(stock)

        payload = {
            "reservation_id": str(reservation.id),
            "product_id": str(product_id),
            "order_id": str(reservation.order_id) if reservation.order_id else None,
            "quantity": reservation.quantity,
            "reason": "manual_release",
        }
        await self._outbox_repo.add(
            InventoryEventType.RESERVATION_RELEASED,
            json.dumps(payload, separators=(",", ":")),
        )

        await self._session.commit()
        await self._session.refresh(reservation)
        await self._session.refresh(stock)
        await self._cache_stock(stock)
        return reservation

    async def expire_reservations(self, batch_size: int = 100) -> int:
        """Release all expired reservations and return the count."""
        now = utc_now()
        expired = await self._reservation_repo.list_expired(now)
        count = 0
        changed_stocks: dict[UUID, StockModel] = {}
        for reservation in expired[:batch_size]:
            stock = await self._stock_repo.get_by_id_for_update(reservation.stock_id)
            if stock is None:
                continue

            reservation.status = ReservationStatus.EXPIRED
            stock.reserved -= reservation.quantity
            stock.available += reservation.quantity
            stock.revision += 1
            await self._reservation_repo.update(reservation)
            await self._stock_repo.update(stock)
            changed_stocks[stock.id] = stock

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
            for stock in changed_stocks.values():
                await self._session.refresh(stock)
                await self._cache_stock(stock)
        return count
