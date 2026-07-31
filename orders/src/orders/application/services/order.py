"""Order application service."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from orders.application.schemas import CreateOrderRequest
from orders.domain.entities import OrderEventType, OrderStatus
from orders.domain.exceptions import DuplicateOrder, InvalidOrderState, OrderNotFound
from orders.infrastructure.models import OrderModel
from orders.infrastructure.repositories.order import OrderRepository, OutboxRepository

if TYPE_CHECKING:
    from orders.application.services.promocode import PromocodeService


class OrderService:
    """Orchestrates order creation and lifecycle."""

    def __init__(
        self,
        session: AsyncSession,
        order_repo: OrderRepository,
        outbox_repo: OutboxRepository,
        promocode_service: PromocodeService | None = None,
    ) -> None:
        self._session = session
        self._order_repo = order_repo
        self._outbox_repo = outbox_repo
        self._promocode_service = promocode_service

    async def create_order(self, data: CreateOrderRequest) -> OrderModel:
        """Create an order from a reservation and request payment."""
        existing = await self._order_repo.get_by_reservation_id(data.reservation_id)
        if existing is not None:
            raise DuplicateOrder

        original_total = Decimal(str(data.price * data.quantity))
        discount_amount = Decimal("0")
        promocode_id = None

        if data.promocode and self._promocode_service:
            promo_res = await self._promocode_service.validate_and_apply(
                code=data.promocode,
                user_id=data.user_id,
                order_amount=original_total,
                for_update=True,
            )
            discount_amount = promo_res.discount_amount
            promocode_id = promo_res.promocode_id

        final_total = original_total - discount_amount
        price_per_item = int(final_total // data.quantity) if discount_amount > 0 else data.price

        order = OrderModel(
            user_id=data.user_id,
            product_id=data.product_id,
            product_name=data.product_name,
            price=price_per_item,
            currency=data.currency,
            quantity=data.quantity,
            status=OrderStatus.AWAITING_PAYMENT,
            reservation_id=data.reservation_id,
            original_price=original_total,
            discount_amount=discount_amount,
            final_price=final_total,
            promocode_id=promocode_id,
        )
        await self._order_repo.create(order)

        if promocode_id and self._promocode_service:
            await self._promocode_service.record_usage(
                promo_id=promocode_id,
                user_id=data.user_id,
                order_id=order.id,
                discount_amount=discount_amount,
            )

        payload = {
            "order_id": str(order.id),
            "reservation_id": str(order.reservation_id),
            "user_id": str(order.user_id),
            "product_id": str(order.product_id),
            "product_name": order.product_name,
            "amount": int(final_total),
            "currency": order.currency,
        }
        await self._outbox_repo.add(
            OrderEventType.ORDER_CREATED,
            json.dumps(payload, separators=(",", ":")),
        )
        await self._outbox_repo.add(
            OrderEventType.PAYMENT_REQUESTED,
            json.dumps(payload, separators=(",", ":")),
        )

        await self._session.commit()
        await self._session.refresh(order)
        return order

    async def confirm_payment(self, order_id: UUID, payment_id: UUID) -> OrderModel:
        """Confirm order after successful payment."""
        order = await self._order_repo.get_by_id(order_id)
        if order is None:
            raise OrderNotFound
        if order.status != OrderStatus.AWAITING_PAYMENT:
            raise InvalidOrderState("Order is not awaiting payment")

        order.status = OrderStatus.CONFIRMED
        order.payment_id = payment_id
        await self._order_repo.update(order)

        payload = {
            "order_id": str(order.id),
            "reservation_id": str(order.reservation_id),
            "payment_id": str(payment_id),
            "user_id": str(order.user_id),
        }
        await self._outbox_repo.add(
            OrderEventType.ORDER_CONFIRMED,
            json.dumps(payload, separators=(",", ":")),
        )

        await self._session.commit()
        await self._session.refresh(order)
        return order

    async def fail_payment(self, order_id: UUID, payment_id: UUID) -> OrderModel:
        """Cancel order after failed payment."""
        order = await self._order_repo.get_by_id(order_id)
        if order is None:
            raise OrderNotFound
        if order.status != OrderStatus.AWAITING_PAYMENT:
            raise InvalidOrderState("Order is not awaiting payment")

        order.status = OrderStatus.PAYMENT_FAILED
        order.payment_id = payment_id
        await self._order_repo.update(order)

        payload = {
            "order_id": str(order.id),
            "reservation_id": str(order.reservation_id),
            "payment_id": str(payment_id),
            "user_id": str(order.user_id),
            "reason": "Payment processing failed",
        }
        await self._outbox_repo.add(
            OrderEventType.ORDER_CANCELLED,
            json.dumps(payload, separators=(",", ":")),
        )

        await self._session.commit()
        await self._session.refresh(order)
        return order

    async def cancel_order(self, order_id: UUID, reason: str = "User cancelled") -> OrderModel:
        """Cancel an order explicitly."""
        order = await self._order_repo.get_by_id(order_id)
        if order is None:
            raise OrderNotFound
        if order.status in (OrderStatus.CONFIRMED, OrderStatus.CANCELLED):
            raise InvalidOrderState("Order cannot be cancelled in its current state")

        order.status = OrderStatus.CANCELLED
        await self._order_repo.update(order)

        payload = {
            "order_id": str(order.id),
            "reservation_id": str(order.reservation_id),
            "user_id": str(order.user_id),
            "reason": reason,
        }
        await self._outbox_repo.add(
            OrderEventType.ORDER_CANCELLED,
            json.dumps(payload, separators=(",", ":")),
        )

        await self._session.commit()
        await self._session.refresh(order)
        return order

    async def get_by_id(self, order_id: UUID) -> OrderModel:
        """Fetch order by ID."""
        order = await self._order_repo.get_by_id(order_id)
        if order is None:
            raise OrderNotFound
        return order

    async def get_by_reservation_id(self, reservation_id: UUID) -> OrderModel:
        """Fetch order by reservation ID."""
        order = await self._order_repo.get_by_reservation_id(reservation_id)
        if order is None:
            raise OrderNotFound
        return order

    async def list_user_orders(
        self, user_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[OrderModel], int]:
        """Fetch paginated orders for a given user."""
        return await self._order_repo.list_user_orders(user_id, limit, offset)
