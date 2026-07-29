"""Order application service."""

from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from orders.application.schemas import CreateOrderRequest
from orders.domain.entities import OrderEventType, OrderStatus
from orders.domain.exceptions import DuplicateOrder, InvalidOrderState, OrderNotFound
from orders.infrastructure.models import OrderModel
from orders.infrastructure.repositories.order import OrderRepository, OutboxRepository


class OrderService:
    """Orchestrates order creation and lifecycle."""

    def __init__(
        self,
        session: AsyncSession,
        order_repo: OrderRepository,
        outbox_repo: OutboxRepository,
    ) -> None:
        self._session = session
        self._order_repo = order_repo
        self._outbox_repo = outbox_repo

    async def create_order(self, data: CreateOrderRequest) -> OrderModel:
        """Create an order from a reservation and request payment."""
        existing = await self._order_repo.get_by_reservation_id(data.reservation_id)
        if existing is not None:
            raise DuplicateOrder

        order = OrderModel(
            user_id=data.user_id,
            product_id=data.product_id,
            product_name=data.product_name,
            price=data.price,
            currency=data.currency,
            quantity=data.quantity,
            status=OrderStatus.AWAITING_PAYMENT,
            reservation_id=data.reservation_id,
        )
        await self._order_repo.create(order)

        payload = {
            "order_id": str(order.id),
            "reservation_id": str(order.reservation_id),
            "user_id": str(order.user_id),
            "product_id": str(order.product_id),
            "product_name": order.product_name,
            "amount": order.price * order.quantity,
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

        order.status = OrderStatus.CANCELLED
        order.payment_id = payment_id
        await self._order_repo.update(order)

        payload = {
            "order_id": str(order.id),
            "reservation_id": str(order.reservation_id),
            "payment_id": str(payment_id),
            "user_id": str(order.user_id),
            "reason": "payment_failed",
        }
        await self._outbox_repo.add(
            OrderEventType.ORDER_CANCELLED,
            json.dumps(payload, separators=(",", ":")),
        )

        await self._session.commit()
        await self._session.refresh(order)
        return order

    async def get_order(self, order_id: UUID) -> OrderModel:
        """Return an order by id."""
        order = await self._order_repo.get_by_id(order_id)
        if order is None:
            raise OrderNotFound
        return order

    async def list_user_orders(
        self,
        user_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[OrderModel], int]:
        """Return a paginated list of a user's orders."""
        items = await self._order_repo.list_by_user(user_id, limit=limit, offset=offset)
        total = len(items)  # pagination requires count query in production
        return list(items), total
