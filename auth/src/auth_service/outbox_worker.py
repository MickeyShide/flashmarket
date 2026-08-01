import asyncio
import json
import logging
from datetime import timedelta

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message
from aio_pika.abc import AbstractRobustExchange
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from auth_service.config import get_settings
from auth_service.database import SessionFactory, engine
from auth_service.models import OutboxEvent
from auth_service.time import utc_now

logger = logging.getLogger(__name__)


async def publish_outbox_batch(
    exchange: AbstractRobustExchange,
    *,
    session_factory: async_sessionmaker[AsyncSession] = SessionFactory,
) -> int:
    """Publish one batch of pending outbox events."""
    settings = get_settings()
    now = utc_now()
    async with session_factory() as db, db.begin():
        events = (
            await db.scalars(
                select(OutboxEvent)
                .where(
                    OutboxEvent.published_at.is_(None),
                    or_(
                        OutboxEvent.next_attempt_at.is_(None),
                        OutboxEvent.next_attempt_at <= now,
                    ),
                )
                .order_by(OutboxEvent.occurred_at)
                .limit(settings.outbox_batch_size)
                .with_for_update(skip_locked=True)
            )
        ).all()
        for event in events:
            try:
                await exchange.publish(
                    Message(
                        body=json.dumps(
                            event.payload,
                            separators=(",", ":"),
                        ).encode("utf-8"),
                        content_type="application/json",
                        delivery_mode=DeliveryMode.PERSISTENT,
                        message_id=str(event.id),
                        type=event.event_type,
                        timestamp=event.occurred_at,
                        headers={
                            "event_id": str(event.id),
                            "aggregate_type": event.aggregate_type,
                            "aggregate_id": str(event.aggregate_id),
                        },
                    ),
                    routing_key=f"identity.{event.event_type}",
                    mandatory=False,
                )
            except Exception as exc:
                event.attempts += 1
                backoff_seconds = min(300, 2 ** min(event.attempts, 8))
                event.next_attempt_at = now + timedelta(seconds=backoff_seconds)
                event.last_error = str(exc)[:1000]
            else:
                event.published_at = utc_now()
                event.attempts += 1
                event.next_attempt_at = None
                event.last_error = None
        return len(events)


async def run_connected_worker() -> None:
    """Keep publishing events while the broker connection is open."""
    settings = get_settings()
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    async with connection:
        channel = await connection.channel(
            publisher_confirms=True,
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
