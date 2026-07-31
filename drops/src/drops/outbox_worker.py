"""Transactional outbox relay to RabbitMQ for drops service."""

from __future__ import annotations

import asyncio
import logging

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message
from aio_pika.abc import AbstractExchange
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from drops.config import get_settings
from drops.domain.entities import DropEventType
from drops.infrastructure.database import SessionFactory, engine, utc_now
from drops.infrastructure.models import OutboxEventModel

logger = logging.getLogger(__name__)


EVENT_ROUTING_KEYS: dict[str, str] = {
    DropEventType.DROP_SCHEDULED: "drops.DropScheduled",
    DropEventType.DROP_STARTED: "drops.DropStarted",
    DropEventType.DROP_ENDED: "drops.DropEnded",
    DropEventType.DROP_CANCELLED: "drops.DropCancelled",
}


async def publish_outbox_batch(
    exchange: AbstractExchange,
    *,
    session_factory: async_sessionmaker[AsyncSession] = SessionFactory,
) -> int:
    """Publish one batch of pending outbox events."""
    settings = get_settings()
    now = utc_now()
    async with session_factory() as db, db.begin():
        events = (
            await db.scalars(
                select(OutboxEventModel)
                .where(
                    OutboxEventModel.status == "pending",
                )
                .order_by(OutboxEventModel.created_at)
                .limit(settings.outbox_batch_size)
                .with_for_update(skip_locked=True)
            )
        ).all()
        for event in events:
            routing_key = EVENT_ROUTING_KEYS.get(
                event.event_type,
                f"drops.{event.event_type}",
            )
            try:
                await exchange.publish(
                    Message(
                        body=event.payload.encode("utf-8"),
                        content_type="application/json",
                        delivery_mode=DeliveryMode.PERSISTENT,
                        message_id=str(event.id),
                        type=event.event_type,
                        timestamp=event.created_at,
                        headers={"event_id": str(event.id)},
                    ),
                    routing_key=routing_key,
                    mandatory=True,
                )
            except Exception as exc:
                event.status = "failed"
                event.attempts = (event.attempts or 0) + 1
                event.published_at = None
                await db.flush()
                logger.warning(
                    "Failed to publish outbox event %s: %s",
                    event.id,
                    exc,
                )
            else:
                event.status = "published"
                event.attempts = (event.attempts or 0) + 1
                event.published_at = now
                await db.flush()
        return len(events)


async def run_connected_worker() -> None:
    """Keep publishing events while the broker connection is open."""
    settings = get_settings()
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    async with connection:
        channel = await connection.channel(
            publisher_confirms=True,
            on_return_raises=True,
        )
        exchange = await channel.declare_exchange(
            settings.rabbitmq_exchange,
            ExchangeType.TOPIC,
            durable=True,
        )
        while True:
            try:
                processed = await publish_outbox_batch(exchange)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Outbox batch failed")
                await asyncio.sleep(settings.outbox_poll_interval_seconds)
                continue
            if processed == 0:
                await asyncio.sleep(settings.outbox_poll_interval_seconds)
            else:
                logger.info("Processed %d outbox event(s)", processed)


async def run_worker() -> None:
    """Reconnect the outbox worker after broker failures."""
    settings = get_settings()
    retry_delay = settings.outbox_poll_interval_seconds
    while True:
        try:
            await run_connected_worker()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Outbox connection failed")
            await asyncio.sleep(retry_delay)
            retry_delay = min(30.0, retry_delay * 2)
        else:
            retry_delay = settings.outbox_poll_interval_seconds


async def run() -> None:
    """Start the worker coroutine."""
    try:
        await run_worker()
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
