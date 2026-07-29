"""Inbound RabbitMQ consumer for inventory service."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import aio_pika
from aio_pika import ExchangeType
from aio_pika.abc import AbstractIncomingMessage
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from inventory.config import get_settings
from inventory.domain.entities import InventoryEventType, ReservationStatus
from inventory.infrastructure.database import SessionFactory, engine
from inventory.infrastructure.repositories.stock import (
    OutboxRepository,
    ReservationRepository,
    StockRepository,
)

logger = logging.getLogger(__name__)

Handler = Callable[[AsyncSession, dict[str, Any]], Awaitable[None]]


async def _emit_inventory_event(
    session: AsyncSession,
    event_type: InventoryEventType,
    payload: dict[str, Any],
) -> None:
    """Persist an outbox event for the inventory saga."""
    outbox = OutboxRepository(session)
    await outbox.add(
        event_type,
        json.dumps(payload, separators=(",", ":")),
    )


async def _find_active_reservation(
    session: AsyncSession,
    order_id: uuid.UUID,
) -> tuple[Any, Any] | None:
    """Return (reservation, stock) for an active reservation bound to order_id."""
    reservation_repo = ReservationRepository(session)
    reservation = await reservation_repo.get_by_order_id(order_id)
    if reservation is None:
        return None

    stock_repo = StockRepository(session)
    stock = await stock_repo.get_by_id(reservation.stock_id)
    if stock is None:
        return None

    return reservation, stock


async def handle_payment_succeeded(
    session: AsyncSession,
    payload: dict[str, Any],
) -> None:
    """Commit reservation after successful payment."""
    order_id = uuid.UUID(str(payload["order_id"]))

    result = await _find_active_reservation(session, order_id)
    if result is None:
        logger.warning("No active reservation for order %s to commit", order_id)
        return
    reservation, stock = result

    if reservation.status != ReservationStatus.RESERVED:
        logger.info(
            "Reservation %s is already in status %s, skip commit",
            reservation.id,
            reservation.status,
        )
        return

    reservation.status = ReservationStatus.COMMITTED
    stock.reserved -= reservation.quantity
    stock.sold += reservation.quantity

    reservation_repo = ReservationRepository(session)
    stock_repo = StockRepository(session)
    await reservation_repo.update(reservation)
    await stock_repo.update(stock)

    await _emit_inventory_event(
        session,
        InventoryEventType.INVENTORY_COMMITTED,
        {
            "reservation_id": str(reservation.id),
            "product_id": str(stock.product_id),
            "order_id": str(order_id),
            "quantity": reservation.quantity,
        },
    )
    logger.info(
        "Committed reservation %s for order %s (qty=%s)",
        reservation.id,
        order_id,
        reservation.quantity,
    )


async def handle_payment_failed(
    session: AsyncSession,
    payload: dict[str, Any],
) -> None:
    """Release reservation after failed payment."""
    order_id = uuid.UUID(str(payload["order_id"]))

    result = await _find_active_reservation(session, order_id)
    if result is None:
        logger.warning("No active reservation for order %s to release", order_id)
        return
    reservation, stock = result

    if reservation.status != ReservationStatus.RESERVED:
        logger.info(
            "Reservation %s is already in status %s, skip release",
            reservation.id,
            reservation.status,
        )
        return

    reservation.status = ReservationStatus.RELEASED
    stock.reserved -= reservation.quantity
    stock.available += reservation.quantity

    reservation_repo = ReservationRepository(session)
    stock_repo = StockRepository(session)
    await reservation_repo.update(reservation)
    await stock_repo.update(stock)

    await _emit_inventory_event(
        session,
        InventoryEventType.RESERVATION_RELEASED,
        {
            "reservation_id": str(reservation.id),
            "product_id": str(stock.product_id),
            "order_id": str(order_id),
            "quantity": reservation.quantity,
            "reason": payload.get("reason", "payment_failed"),
        },
    )
    logger.info(
        "Released reservation %s for order %s (qty=%s)",
        reservation.id,
        order_id,
        reservation.quantity,
    )


async def handle_order_cancelled(
    session: AsyncSession,
    payload: dict[str, Any],
) -> None:
    """Release reservation when order is cancelled."""
    order_id = uuid.UUID(str(payload["order_id"]))

    result = await _find_active_reservation(session, order_id)
    if result is None:
        logger.warning("No active reservation for order %s to release", order_id)
        return
    reservation, stock = result

    if reservation.status != ReservationStatus.RESERVED:
        logger.info(
            "Reservation %s is already in status %s, skip release",
            reservation.id,
            reservation.status,
        )
        return

    reservation.status = ReservationStatus.RELEASED
    stock.reserved -= reservation.quantity
    stock.available += reservation.quantity

    reservation_repo = ReservationRepository(session)
    stock_repo = StockRepository(session)
    await reservation_repo.update(reservation)
    await stock_repo.update(stock)

    await _emit_inventory_event(
        session,
        InventoryEventType.RESERVATION_RELEASED,
        {
            "reservation_id": str(reservation.id),
            "product_id": str(stock.product_id),
            "order_id": str(order_id),
            "quantity": reservation.quantity,
            "reason": payload.get("reason", "order_cancelled"),
        },
    )
    logger.info(
        "Released reservation %s after order %s cancellation",
        reservation.id,
        order_id,
    )


HANDLERS: dict[str, Handler] = {
    "payments.PaymentSucceeded": handle_payment_succeeded,
    "payments.PaymentFailed": handle_payment_failed,
    "orders.OrderCancelled": handle_order_cancelled,
}


async def process_message(
    message: AbstractIncomingMessage,
    *,
    session_factory: async_sessionmaker[AsyncSession] = SessionFactory,
) -> None:
    """Route an incoming message to its handler."""
    async with message.process(reject_on_redelivered=False):
        body = json.loads(message.body.decode("utf-8"))
        routing_key = message.routing_key or ""
        handler = HANDLERS.get(routing_key)
        if handler is None:
            logger.warning("No handler for routing key %s", routing_key)
            return

        async with session_factory() as session, session.begin():
            await handler(session, body)


async def run_consumer() -> None:
    """Connect to RabbitMQ and consume saga events."""
    settings = get_settings()
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=10)
        exchange = await channel.declare_exchange(
            settings.rabbitmq_exchange,
            ExchangeType.TOPIC,
            durable=True,
        )
        queue = await channel.declare_queue(
            "inventory.events",
            durable=True,
        )
        for routing_key in HANDLERS:
            await queue.bind(exchange, routing_key=routing_key)

        async with queue.iterator() as iterator:
            async for message in iterator:
                try:
                    await process_message(message)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("Failed to process message")


async def run() -> None:
    """Start the consumer coroutine."""
    try:
        await run_consumer()
    finally:
        await engine.dispose()


def main() -> None:
    """Run this module as a command-line entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    asyncio.run(run())


if __name__ == "__main__":
    main()
