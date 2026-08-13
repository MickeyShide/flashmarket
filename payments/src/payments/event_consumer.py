"""Inbound RabbitMQ consumer for payments service."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime
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

from payments.config import get_settings
from payments.domain.entities import PaymentStatus
from payments.infrastructure.database import SessionFactory, engine
from payments.infrastructure.models import PaymentModel
from payments.infrastructure.repositories.payment import PaymentRepository

logger = logging.getLogger(__name__)

Handler = Callable[[AsyncSession, dict[str, Any]], Awaitable[None]]


async def handle_payment_requested(
    session: AsyncSession,
    payload: dict[str, Any],
) -> None:
    """Create a pending payment when an order requests one."""
    order_id = uuid.UUID(str(payload["order_id"]))
    user_id = uuid.UUID(str(payload["user_id"]))
    amount = int(payload["amount"])
    currency = str(payload.get("currency", "RUB"))
    expires_at = (
        datetime.fromisoformat(str(payload["payment_expires_at"]))
        if payload.get("payment_expires_at")
        else None
    )

    payment_repo = PaymentRepository(session)

    existing = await payment_repo.get_by_order_id(order_id)
    if existing is not None:
        logger.info("Payment already exists for order %s", order_id)
        return

    payment = PaymentModel(
        order_id=order_id,
        user_id=user_id,
        amount=amount,
        currency=currency,
        provider="mock",
        status=PaymentStatus.PENDING,
        expires_at=expires_at,
    )
    await payment_repo.create(payment)
    logger.info("Created payment %s for order %s", payment.id, order_id)


HANDLERS: dict[str, Handler] = {
    "orders.PaymentRequested": handle_payment_requested,
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
            await handler(session, body)
    except (KeyError, TypeError, ValueError) as exc:
        raise PermanentMessageError("invalid payments event payload") from exc


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
            queue_name="payments.events",
            topic_exchange=exchange,
            routing_keys=("orders.PaymentRequested",),
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
        await run_forever(run_consumer, label="Payments consumer")
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
