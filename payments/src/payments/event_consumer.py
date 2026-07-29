"""Inbound RabbitMQ consumer for payments service."""

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
            "payments.events",
            durable=True,
        )
        await queue.bind(exchange, routing_key="orders.PaymentRequested")

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
