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
from rabbitmq_reliability import (
    PermanentMessageError,
    ReliabilityConfig,
    declare_consumer_topology,
    decode_json_object,
    original_routing_key,
    periodic_heartbeat,
    process_with_retries,
    run_forever,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from inventory.application.contracts import StockCache
from inventory.application.schemas import StockResponse
from inventory.config import get_settings
from inventory.domain.entities import InventoryEventType, ReservationStatus
from inventory.infrastructure.database import SessionFactory, engine
from inventory.infrastructure.models import ReservationModel, StockModel
from inventory.infrastructure.repositories.stock import (
    OutboxRepository,
    ReservationRepository,
    StockRepository,
)
from inventory.infrastructure.stock_cache import redis_client, stock_cache

logger = logging.getLogger(__name__)

Handler = Callable[[AsyncSession, dict[str, Any]], Awaitable[StockModel | None]]


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
    payload: dict[str, Any],
) -> tuple[ReservationModel, StockModel] | None:
    """Return (reservation, stock) for an active reservation bound to order_id or reservation_id."""
    reservation_repo = ReservationRepository(session)
    reservation = None
    if "order_id" in payload and payload["order_id"]:
        try:
            order_id = uuid.UUID(str(payload["order_id"]))
            reservation = await reservation_repo.get_by_order_id(order_id)
        except ValueError, TypeError:
            pass

    if reservation is None and "reservation_id" in payload and payload["reservation_id"]:
        try:
            res_id = uuid.UUID(str(payload["reservation_id"]))
            reservation = await reservation_repo.get_by_id(res_id)
        except ValueError, TypeError:
            pass

    if reservation is None:
        return None

    stock_repo = StockRepository(session)
    stock = await stock_repo.get_by_id_for_update(reservation.stock_id)
    if stock is None:
        return None

    return reservation, stock


async def handle_payment_succeeded(
    session: AsyncSession,
    payload: dict[str, Any],
) -> StockModel | None:
    """Commit reservation after successful payment."""
    order_id = payload.get("order_id")

    result = await _find_active_reservation(session, payload)
    if result is None:
        logger.warning("No active reservation for order/payload %s to commit", payload)
        return None
    reservation, stock = result

    if reservation.status != ReservationStatus.RESERVED:
        logger.info(
            "Reservation %s is already in status %s, skip commit",
            reservation.id,
            reservation.status,
        )
        return None

    reservation.status = ReservationStatus.COMMITTED
    stock.reserved -= reservation.quantity
    stock.sold += reservation.quantity
    stock.revision += 1

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
            "order_id": str(order_id) if order_id else None,
            "quantity": reservation.quantity,
        },
    )
    logger.info(
        "Committed reservation %s for order %s (qty=%s)",
        reservation.id,
        order_id,
        reservation.quantity,
    )
    return stock


async def handle_payment_failed(
    session: AsyncSession,
    payload: dict[str, Any],
) -> StockModel | None:
    """Release reservation after failed payment."""
    order_id = payload.get("order_id")

    result = await _find_active_reservation(session, payload)
    if result is None:
        logger.warning("No active reservation for order/payload %s to release", payload)
        return None
    reservation, stock = result

    if reservation.status != ReservationStatus.RESERVED:
        logger.info(
            "Reservation %s is already in status %s, skip release",
            reservation.id,
            reservation.status,
        )
        return None

    reservation.status = ReservationStatus.RELEASED
    stock.reserved -= reservation.quantity
    stock.available += reservation.quantity
    stock.revision += 1

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
            "order_id": str(order_id) if order_id else None,
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
    return stock


async def handle_order_cancelled(
    session: AsyncSession,
    payload: dict[str, Any],
) -> StockModel | None:
    """Release reservation when order is cancelled."""
    order_id = payload.get("order_id")

    result = await _find_active_reservation(session, payload)
    if result is None:
        logger.warning("No active reservation for order %s to release", order_id)
        return None
    reservation, stock = result

    if reservation.status != ReservationStatus.RESERVED:
        logger.info(
            "Reservation %s is already in status %s, skip release",
            reservation.id,
            reservation.status,
        )
        return None

    reservation.status = ReservationStatus.RELEASED
    stock.reserved -= reservation.quantity
    stock.available += reservation.quantity
    stock.revision += 1

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
            "order_id": str(order_id) if order_id else None,
            "quantity": reservation.quantity,
            "reason": payload.get("reason", "order_cancelled"),
        },
    )
    logger.info(
        "Released reservation %s after order %s cancellation",
        reservation.id,
        order_id,
    )
    return stock


async def handle_order_created(
    session: AsyncSession,
    payload: dict[str, Any],
) -> StockModel | None:
    """Bind reservation to order_id when order is created."""
    reservation_id_str = payload.get("reservation_id")
    order_id_str = payload.get("order_id")
    if not reservation_id_str or not order_id_str:
        return None
    try:
        res_id = uuid.UUID(str(reservation_id_str))
        order_id = uuid.UUID(str(order_id_str))
    except ValueError, TypeError:
        return None

    reservation_repo = ReservationRepository(session)
    reservation = await reservation_repo.get_by_id(res_id)
    if reservation is not None and reservation.order_id is None:
        reservation.order_id = order_id
        await reservation_repo.update(reservation)
        logger.info("Bound reservation %s to order %s", res_id, order_id)
    return None


HANDLERS: dict[str, Handler] = {
    "orders.OrderCreated": handle_order_created,
    "payments.PaymentSucceeded": handle_payment_succeeded,
    "payments.PaymentFailed": handle_payment_failed,
    "orders.OrderCancelled": handle_order_cancelled,
}


async def process_message(
    message: AbstractIncomingMessage,
    *,
    session_factory: async_sessionmaker[AsyncSession] = SessionFactory,
    cache: StockCache = stock_cache,
) -> None:
    """Route an incoming message to its handler."""
    body = decode_json_object(message)
    routing_key = original_routing_key(message)
    handler = HANDLERS.get(routing_key)
    if handler is None:
        raise PermanentMessageError(f"unsupported routing key: {routing_key}")

    changed_stock: StockModel | None = None
    try:
        async with session_factory() as session:
            async with session.begin():
                changed_stock = await handler(session, body)
            if changed_stock is not None:
                snapshot = StockResponse.model_validate(changed_stock)
                await cache.store_stock(snapshot, changed_stock.revision)
    except (KeyError, TypeError, ValueError) as exc:
        raise PermanentMessageError("invalid inventory event payload") from exc


async def run_consumer() -> None:
    """Connect to RabbitMQ and consume saga events."""
    settings = get_settings()
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    async with connection:
        channel = await connection.channel(publisher_confirms=True, on_return_raises=True)
        await channel.set_qos(prefetch_count=10)
        exchange = await channel.declare_exchange(
            settings.rabbitmq_exchange,
            ExchangeType.TOPIC,
            durable=True,
        )
        topology = await declare_consumer_topology(
            channel,
            queue_name="inventory.events",
            topic_exchange=exchange,
            routing_keys=tuple(HANDLERS),
            config=ReliabilityConfig(),
        )
        async with periodic_heartbeat("/tmp/flashmarket-heartbeat.json"):
            async with topology.queue.iterator() as iterator:
                async for message in iterator:
                    try:
                        await process_with_retries(
                            message,
                            handler=process_message,
                            topology=topology,
                            config=ReliabilityConfig(),
                        )
                    except asyncio.CancelledError:
                        raise
                    except Exception:
                        logger.exception("Failed to process message")


async def run() -> None:
    """Start the consumer coroutine."""
    try:
        await run_forever(run_consumer, label="Inventory consumer")
    finally:
        await redis_client.aclose()
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
