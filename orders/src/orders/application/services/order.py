"""Order application service."""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from orders.application.schemas import CreateOrderBatchRequest, CreateOrderRequest
from orders.domain.entities import OrderEventType, OrderStatus
from orders.domain.exceptions import DuplicateOrder, InvalidOrderState, OrderNotFound
from orders.infrastructure.models import OrderModel
from orders.infrastructure.repositories.order import OrderRepository, OutboxRepository

if TYPE_CHECKING:
    from orders.application.services.promocode import PromocodeService
    from orders.infrastructure.catalog_client import CatalogClient


@dataclass(frozen=True, slots=True)
class BatchOrderResult:
    checkout_id: UUID
    orders: list[OrderModel]
    original_amount: Decimal
    discount_amount: Decimal
    final_amount: Decimal


class OrderService:
    """Orchestrates order creation and lifecycle."""

    def __init__(
        self,
        session: AsyncSession,
        order_repo: OrderRepository,
        outbox_repo: OutboxRepository,
        promocode_service: PromocodeService | None = None,
        catalog_client: CatalogClient | None = None,
    ) -> None:
        self._session = session
        self._order_repo = order_repo
        self._outbox_repo = outbox_repo
        self._promocode_service = promocode_service
        self._catalog_client = catalog_client

    async def create_order(self, data: CreateOrderRequest) -> OrderModel:
        """Create an order from a reservation and request payment."""
        existing = await self._order_repo.get_by_reservation_id(data.reservation_id)
        if existing is not None:
            raise DuplicateOrder

        price = data.price
        currency = data.currency
        if self._catalog_client:
            cat_price = await self._catalog_client.get_price(
                data.product_id, variant_id=data.variant_id
            )
            if cat_price is None:
                raise InvalidOrderState(
                    "Unable to verify authoritative price from catalog for product "
                    f"{data.product_id}"
                )
            if cat_price.price != Decimal(str(data.price)):
                raise InvalidOrderState(
                    f"Price mismatch: provided {data.price}, authoritative is {cat_price.price}"
                )
            price = int(cat_price.price)
            currency = cat_price.currency

        original_total = Decimal(str(price * data.quantity))
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
        status = OrderStatus.CONFIRMED if final_total == 0 else OrderStatus.AWAITING_PAYMENT
        order = OrderModel(
            user_id=data.user_id,
            product_id=data.product_id,
            product_name=data.product_name,
            price=price,
            currency=currency,
            quantity=data.quantity,
            status=status,
            reservation_id=data.reservation_id,
            original_price=original_total,
            discount_amount=discount_amount,
            final_price=final_total,
            promocode_id=promocode_id,
            variant_id=data.variant_id,
            variant_sku=data.variant_sku,
            variant_size=data.variant_size,
            variant_color=data.variant_color,
            drop_id=data.drop_id,
            payment_expires_at=data.payment_expires_at,
        )
        try:
            await self._order_repo.create(order)

            if promocode_id and self._promocode_service:
                await self._promocode_service.record_usage(
                    promo_id=promocode_id,
                    user_id=data.user_id,
                    order_id=order.id,
                    discount_amount=discount_amount,
                )

            receipt_snapshot: dict[str, object] = {
                "currency": order.currency,
                "total_amount": int(final_total),
                "items": [
                    {
                        "description": order.product_name[:128],
                        "quantity": str(data.quantity),
                        "unit_amount": int(final_total // data.quantity) if data.quantity else int(final_total),
                        "vat_code": 1,
                        "payment_subject": "commodity",
                        "payment_mode": "full_payment",
                        "measure": "piece",
                    }
                ],
            }
            if data.receipt_email is not None:
                receipt_snapshot["customer"] = {"email": data.receipt_email}
            payload = {
                "order_id": str(order.id),
                "reservation_id": str(order.reservation_id),
                "user_id": str(order.user_id),
                "product_id": str(order.product_id),
                "product_name": order.product_name,
                "amount": int(final_total),
                "currency": order.currency,
                "payment_expires_at": (
                    order.payment_expires_at.isoformat() if order.payment_expires_at else None
                ),
                "receipt_snapshot": receipt_snapshot,
            }
            await self._outbox_repo.add(
                OrderEventType.ORDER_CREATED,
                json.dumps(payload, separators=(",", ":")),
            )
            if final_total == 0:
                confirmed_payload = {
                    "order_id": str(order.id),
                    "reservation_id": str(order.reservation_id),
                    "user_id": str(order.user_id),
                }
                await self._outbox_repo.add(
                    OrderEventType.ORDER_CONFIRMED,
                    json.dumps(confirmed_payload, separators=(",", ":")),
                )
            else:
                await self._outbox_repo.add(
                    OrderEventType.PAYMENT_REQUESTED,
                    json.dumps(payload, separators=(",", ":")),
                )

            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise DuplicateOrder from exc

        await self._session.refresh(order)
        return order

    async def create_batch(self, data: CreateOrderBatchRequest) -> BatchOrderResult:
        """Create all checkout lines atomically and consume one optional promo."""
        for line in data.lines:
            if await self._order_repo.get_by_reservation_id(line.reservation_id) is not None:
                raise DuplicateOrder
            if self._catalog_client:
                cat_price = await self._catalog_client.get_price(
                    line.product_id, variant_id=line.variant_id
                )
                if cat_price is None:
                    raise InvalidOrderState(
                        "Unable to verify authoritative price from catalog for product "
                        f"{line.product_id}"
                    )
                if cat_price.price != Decimal(str(line.price)):
                    raise InvalidOrderState(
                        f"Price mismatch for {line.product_id}: "
                        f"provided {line.price}, authoritative is {cat_price.price}"
                    )

        line_totals = [Decimal(line.price * line.quantity) for line in data.lines]
        original_amount = sum(line_totals, Decimal("0"))
        total_discount = Decimal("0")
        promocode_id: UUID | None = None
        if data.promocode_code and self._promocode_service:
            result = await self._promocode_service.validate_and_apply(
                code=data.promocode_code,
                user_id=data.lines[0].user_id,
                order_amount=original_amount,
                for_update=True,
            )
            total_discount = min(result.discount_amount, original_amount)
            promocode_id = result.promocode_id

        discount_units = int(total_discount.to_integral_value(rounding=ROUND_FLOOR))
        allocations = [0 for _ in data.lines]
        if discount_units and original_amount > 0:
            exact = [Decimal(discount_units) * total / original_amount for total in line_totals]
            allocations = [int(value.to_integral_value(rounding=ROUND_FLOOR)) for value in exact]
            remainder = discount_units - sum(allocations)
            allocation_order = sorted(
                range(len(exact)),
                key=lambda index: (exact[index] - allocations[index], -index),
                reverse=True,
            )
            for index in allocation_order[:remainder]:
                allocations[index] += 1

        checkout_id = uuid4()
        orders: list[OrderModel] = []
        for line, original, allocated in zip(data.lines, line_totals, allocations, strict=True):
            discount = Decimal(allocated)
            final = original - discount
            status = OrderStatus.CONFIRMED if final == 0 else OrderStatus.AWAITING_PAYMENT
            order = OrderModel(
                checkout_id=checkout_id,
                user_id=line.user_id,
                product_id=line.product_id,
                product_name=line.product_name,
                price=line.price,
                currency=line.currency,
                quantity=line.quantity,
                status=status,
                reservation_id=line.reservation_id,
                original_price=original,
                discount_amount=discount,
                final_price=final,
                promocode_id=promocode_id if discount > 0 else None,
                variant_id=line.variant_id,
                variant_sku=line.variant_sku,
                variant_size=line.variant_size,
                variant_color=line.variant_color,
                drop_id=line.drop_id,
                payment_expires_at=line.payment_expires_at,
            )
            await self._order_repo.create(order)
            receipt_email = data.receipt_email or line.receipt_email
            receipt_snapshot: dict[str, object] = {
                "currency": order.currency,
                "total_amount": int(final),
                "items": [
                    {
                        "description": order.product_name[:128],
                        "quantity": str(line.quantity),
                        "unit_amount": int(final // line.quantity) if line.quantity else int(final),
                        "vat_code": 1,
                        "payment_subject": "commodity",
                        "payment_mode": "full_payment",
                        "measure": "piece",
                    }
                ],
            }
            if receipt_email is not None:
                receipt_snapshot["customer"] = {"email": receipt_email}
            payload = {
                "order_id": str(order.id),
                "checkout_id": str(checkout_id),
                "reservation_id": str(order.reservation_id),
                "user_id": str(order.user_id),
                "product_id": str(order.product_id),
                "product_name": order.product_name,
                "amount": int(final),
                "currency": order.currency,
                "payment_expires_at": (
                    order.payment_expires_at.isoformat() if order.payment_expires_at else None
                ),
                "receipt_snapshot": receipt_snapshot,
            }
            await self._outbox_repo.add(
                OrderEventType.ORDER_CREATED,
                json.dumps(payload, separators=(",", ":")),
            )
            if final == 0:
                confirmed_payload = {
                    "order_id": str(order.id),
                    "reservation_id": str(order.reservation_id),
                    "user_id": str(order.user_id),
                }
                await self._outbox_repo.add(
                    OrderEventType.ORDER_CONFIRMED,
                    json.dumps(confirmed_payload, separators=(",", ":")),
                )
            else:
                await self._outbox_repo.add(
                    OrderEventType.PAYMENT_REQUESTED,
                    json.dumps(payload, separators=(",", ":")),
                )
            orders.append(order)

        try:
            if promocode_id and self._promocode_service:
                first_usage = True
                for ord_item, alloc in zip(orders, allocations, strict=True):
                    if alloc > 0:
                        await self._promocode_service.record_usage(
                            promo_id=promocode_id,
                            user_id=ord_item.user_id,
                            order_id=ord_item.id,
                            discount_amount=Decimal(alloc),
                            increment_uses=first_usage,
                        )
                        first_usage = False

            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise DuplicateOrder from exc

        for order in orders:
            await self._session.refresh(order)
        return BatchOrderResult(
            checkout_id=checkout_id,
            orders=orders,
            original_amount=original_amount,
            discount_amount=Decimal(discount_units),
            final_amount=original_amount - Decimal(discount_units),
        )

    async def confirm_payment(self, order_id: UUID, payment_id: UUID) -> OrderModel:
        """Confirm order after successful payment."""
        order = await self._order_repo.get_by_id_for_update(order_id)
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
        order = await self._order_repo.get_by_id_for_update(order_id)
        if order is None:
            raise OrderNotFound
        if order.status != OrderStatus.AWAITING_PAYMENT:
            raise InvalidOrderState("Order is not awaiting payment")

        order.status = OrderStatus.CANCELLED
        order.payment_id = payment_id
        await self._order_repo.update(order)

        if order.promocode_id and self._promocode_service:
            await self._promocode_service.rollback_usage(order.promocode_id, order.id)

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
        order = await self._order_repo.get_by_id_for_update(order_id)
        if order is None:
            raise OrderNotFound
        if order.status in (OrderStatus.CONFIRMED, OrderStatus.CANCELLED):
            raise InvalidOrderState("Order cannot be cancelled in its current state")

        order.status = OrderStatus.CANCELLED
        await self._order_repo.update(order)

        if order.promocode_id and self._promocode_service:
            await self._promocode_service.rollback_usage(order.promocode_id, order.id)

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
        items = list(await self._order_repo.list_by_user(user_id, limit=limit, offset=offset))
        total = await self._order_repo.count_by_user(user_id)
        return items, total
