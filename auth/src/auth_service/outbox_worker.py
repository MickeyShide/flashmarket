import asyncio
import json
import logging

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message
from aio_pika.abc import AbstractRobustExchange
from rabbitmq_reliability import (
    claim_outbox_event,
    publish_confirmed,
    record_outbox_result,
    run_forever,
    touch_heartbeat,
)
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
    processed = 0
    for _ in range(settings.outbox_batch_size):
        claimed = await claim_outbox_event(session_factory, OutboxEvent, utc_now())
        if claimed is None:
            break
        event, token = claimed
        error: Exception | None = None
        try:
            await publish_confirmed(
                exchange,
                Message(
                    body=json.dumps(event.payload, separators=(",", ":")).encode("utf-8"),
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
                f"identity.{event.event_type}",
                timeout_seconds=5.0,
                mandatory=False,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            error = exc
            logger.warning("Failed to publish outbox event %s: %s", event.id, exc)
        await record_outbox_result(session_factory, OutboxEvent, event.id, token, utc_now(), error)
        processed += 1
    return processed


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
            if processed:
                logger.info("Processed %d outbox event(s)", processed)
            touch_heartbeat("/tmp/flashmarket-heartbeat.json", "poll_complete")
            await asyncio.sleep(settings.outbox_poll_interval_seconds)


async def run_worker() -> None:
    """Reconnect the outbox worker after broker failures."""
    settings = get_settings()
    await run_forever(
        run_connected_worker,
        initial_delay=settings.outbox_poll_interval_seconds,
        label="Auth outbox",
    )


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
