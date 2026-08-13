"""Inbound RabbitMQ consumer for orders service."""

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
    begin_event_once,
    declare_consumer_topology,
    decode_json_object,
    delivery_identity,
    original_routing_key,
    periodic_heartbeat,
    process_with_retries,
    run_forever,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from orders.config import get_settings
from orders.domain.entities import OrderEventType, OrderStatus
from orders.infrastructure.database import SessionFactory, engine
from orders.infrastructure.models import ProcessedEventModel
from orders.infrastructure.repositories.order import OrderRepository, OutboxRepository

logger = logging.getLogger(__name__)

Handler = Callable[[AsyncSession, dict[str, Any]], Awaitable[None]]


async def _emit_order_event(
    session: AsyncSession,
    event_type: OrderEventType,
    payload: dict[str, Any],
) -> None:
    """Persist an outbox event for the order saga."""
    outbox = OutboxRepository(session)
    await outbox.add(
        event_type,
        json.dumps(payload, separators=(",", ":")),
    )


async def handle_payment_succeeded(
    session: AsyncSession,
    payload: dict[str, Any],
) -> None:
    """Confirm order after successful payment."""
    order_id = uuid.UUID(str(payload["order_id"]))
    payment_id = uuid.UUID(str(payload["payment_id"]))

    order_repo = OrderRepository(session)
    order = await order_repo.get_by_id(order_id)
    if order is None:
        logger.warning("Order %s not found for payment success", order_id)
        return
    if order.status == OrderStatus.CONFIRMED:
        logger.info("Order %s already confirmed", order_id)
        return
    if order.status != OrderStatus.AWAITING_PAYMENT:
        logger.warning(
            "Order %s cannot be confirmed from status %s",
            order_id,
            order.status,
        )
        return

    order.payment_id = payment_id
    order.status = OrderStatus.CONFIRMED
    await order_repo.update(order)

    await _emit_order_event(
        session,
        OrderEventType.ORDER_CONFIRMED,
        {
            "order_id": str(order.id),
            "reservation_id": str(order.reservation_id),
            "payment_id": str(payment_id),
            "user_id": str(order.user_id),
        },
    )
    logger.info("Confirmed order %s with payment %s", order_id, payment_id)


async def handle_payment_failed(
    session: AsyncSession,
    payload: dict[str, Any],
) -> None:
    """Cancel order after failed payment."""
    order_id = uuid.UUID(str(payload["order_id"]))
    payment_id = uuid.UUID(str(payload["payment_id"]))

    order_repo = OrderRepository(session)
    order = await order_repo.get_by_id(order_id)
    if order is None:
        logger.warning("Order %s not found for payment failure", order_id)
        return
    if order.status == OrderStatus.CANCELLED:
        logger.info("Order %s already cancelled", order_id)
        return
    if order.status != OrderStatus.AWAITING_PAYMENT:
        logger.warning(
            "Order %s cannot be cancelled from status %s",
            order_id,
            order.status,
        )
        return

    order.payment_id = payment_id
    order.status = OrderStatus.CANCELLED
    await order_repo.update(order)

    await _emit_order_event(
        session,
        OrderEventType.ORDER_CANCELLED,
        {
            "order_id": str(order.id),
            "reservation_id": str(order.reservation_id),
            "payment_id": str(payment_id),
            "user_id": str(order.user_id),
            "reason": payload.get("reason", "payment_failed"),
        },
    )
    logger.info("Cancelled order %s after failed payment %s", order_id, payment_id)


async def handle_reservation_released(
    session: AsyncSession,
    payload: dict[str, Any],
) -> None:
    """Cancel order when its reservation was released."""
    order_id = payload.get("order_id")
    if order_id is None:
        return
    order_id = uuid.UUID(str(order_id))

    order_repo = OrderRepository(session)
    order = await order_repo.get_by_id(order_id)
    if order is None:
        return
    if order.status not in (OrderStatus.AWAITING_PAYMENT, OrderStatus.PENDING):
        return

    order.status = OrderStatus.CANCELLED
    await order_repo.update(order)

    await _emit_order_event(
        session,
        OrderEventType.ORDER_CANCELLED,
        {
            "order_id": str(order.id),
            "reservation_id": str(order.reservation_id),
            "user_id": str(order.user_id),
            "reason": payload.get("reason", "reservation_released"),
        },
    )
    logger.info("Cancelled order %s due to reservation release", order_id)


HANDLERS: dict[str, Handler] = {
    "payments.PaymentSucceeded": handle_payment_succeeded,
    "payments.PaymentFailed": handle_payment_failed,
    "inventory.ReservationReleased": handle_reservation_released,
}


async def process_message(
    message: AbstractIncomingMessage,
    *,
    session_factory: async_sessionmaker[AsyncSession] = SessionFactory,
) -> None:
    """Route an incoming message to its handler."""
    body = decode_json_object(message)
    routing_key = original_routing_key(message)
    handler = HANDLERS.get(routing_key)
    if handler is None:
        raise PermanentMessageError(f"unsupported routing key: {routing_key}")
    try:
        async with session_factory() as session, session.begin():
            if not await begin_event_once(
                session,
                ProcessedEventModel,
                event_id=delivery_identity(message, routing_key),
                routing_key=routing_key,
            ):
                logger.info("Skipping duplicate event %s", delivery_identity(message, routing_key))
                return
            await handler(session, body)
    except (KeyError, TypeError, ValueError) as exc:
        raise PermanentMessageError("invalid orders event payload") from exc


async def run_consumer() -> None:
    """Connect to RabbitMQ and consume saga events."""
    settings = get_settings()
    reliability = ReliabilityConfig.from_settings(settings)
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
            queue_name="orders.events",
            topic_exchange=exchange,
            routing_keys=tuple(HANDLERS),
            config=reliability,
        )
        async with periodic_heartbeat(
            "/tmp/flashmarket-heartbeat.json",
            interval_seconds=settings.worker_heartbeat_interval_seconds,
            phase="orders_consumer",
        ):
            async with topology.queue.iterator() as iterator:
                async for message in iterator:
                    try:
                        await process_with_retries(
                            message,
                            handler=process_message,
                            topology=topology,
                            config=reliability,
                        )
                    except asyncio.CancelledError:
                        raise
                    except Exception:
                        logger.exception("Failed to process message")


async def run() -> None:
    """Start the consumer coroutine."""
    try:
        settings = get_settings()
        await run_forever(
            run_consumer,
            initial_delay=settings.rabbitmq_reconnect_initial_seconds,
            max_delay=settings.rabbitmq_reconnect_max_seconds,
            label="Orders consumer",
        )
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
