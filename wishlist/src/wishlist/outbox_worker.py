"""Confirmed transactional outbox relay for Wishlist notifications."""

from __future__ import annotations

import asyncio
import logging

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message
from aio_pika.abc import AbstractExchange
from rabbitmq_reliability import (
    claim_outbox_event,
    publish_confirmed,
    record_outbox_result,
    run_forever,
    touch_heartbeat,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from wishlist.config import get_settings
from wishlist.infrastructure.database import SessionFactory, engine, utc_now
from wishlist.infrastructure.models import OutboxEventModel

logger = logging.getLogger(__name__)


async def publish_outbox_batch(
    exchange: AbstractExchange,
    *,
    session_factory: async_sessionmaker[AsyncSession] = SessionFactory,
) -> int:
    settings = get_settings()
    processed = 0
    for _ in range(settings.outbox_batch_size):
        claimed = await claim_outbox_event(session_factory, OutboxEventModel, utc_now())
        if claimed is None:
            break
        event, token = claimed
        error: Exception | None = None
        try:
            await publish_confirmed(
                exchange,
                Message(
                    body=event.payload.encode("utf-8"),
                    content_type="application/json",
                    delivery_mode=DeliveryMode.PERSISTENT,
                    message_id=str(event.id),
                    type=event.event_type,
                    timestamp=event.created_at,
                    headers={"event_id": str(event.id), "event_key": event.event_key},
                ),
                "wishlist.DropAvailable",
                timeout_seconds=settings.rabbitmq_publish_timeout_seconds,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            error = exc
            logger.warning("Failed to publish outbox event %s: %s", event.id, exc)
        await record_outbox_result(
            session_factory, OutboxEventModel, event.id, token, utc_now(), error
        )
        processed += 1
    return processed


async def run_connected_worker() -> None:
    settings = get_settings()
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    async with connection:
        channel = await connection.channel(publisher_confirms=True, on_return_raises=True)
        exchange = await channel.declare_exchange(
            settings.rabbitmq_exchange, ExchangeType.TOPIC, durable=True
        )
        while True:
            processed = await publish_outbox_batch(exchange)
            if processed:
                logger.info("Processed %d Wishlist outbox event(s)", processed)
            touch_heartbeat("/tmp/flashmarket-heartbeat.json", "poll_complete")
            await asyncio.sleep(settings.outbox_poll_interval_seconds)


async def run() -> None:
    settings = get_settings()
    try:
        await run_forever(
            run_connected_worker,
            initial_delay=settings.outbox_poll_interval_seconds,
            label="Wishlist outbox",
        )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
