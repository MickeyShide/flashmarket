"""Translate drop starts into notifications for users watching its products."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from uuid import UUID

import aio_pika
from aio_pika import ExchangeType
from aio_pika.abc import AbstractIncomingMessage
from rabbitmq_reliability import (
    PermanentMessageError,
    ReliabilityConfig,
    declare_consumer_topology,
    decode_json_object,
    periodic_heartbeat,
    process_with_retries,
    run_forever,
)

from wishlist.config import get_settings
from wishlist.infrastructure.database import SessionFactory, engine
from wishlist.infrastructure.repositories.wishlist import WishlistRepository

logger = logging.getLogger(__name__)

INITIAL_RECONNECT_DELAY_SECONDS = 1.0
MAX_RECONNECT_DELAY_SECONDS = 30.0


async def process_drop_started(
    message: AbstractIncomingMessage,
) -> None:
    payload = decode_json_object(message)
    try:
        product_ids = [UUID(value) for value in payload.get("product_ids", [])]
        if not product_ids:
            return
        drop_id = str(payload["drop_id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise PermanentMessageError("invalid DropStarted payload") from exc

    async with SessionFactory() as session, session.begin():
        repository = WishlistRepository(session)
        users = await repository.get_users_for_products(product_ids)
        staged = await repository.stage_drop_notifications(
            drop_id=drop_id,
            drop_name=str(payload.get("name") or "Flash drop"),
            drop_slug=str(payload.get("slug") or ""),
            user_ids=users,
        )
    logger.info("Staged drop %s for %d wishlist users", drop_id, staged)


async def run_consumer() -> None:
    settings = get_settings()
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    async with connection:
        channel = await connection.channel(publisher_confirms=True, on_return_raises=True)
        await channel.set_qos(prefetch_count=10)
        exchange = await channel.declare_exchange(
            settings.rabbitmq_exchange, ExchangeType.TOPIC, durable=True
        )
        topology = await declare_consumer_topology(
            channel,
            queue_name="wishlist.drop-events",
            topic_exchange=exchange,
            routing_keys=("drops.DropStarted",),
            config=ReliabilityConfig(),
        )
        async with periodic_heartbeat("/tmp/flashmarket-heartbeat.json"):
            async with topology.queue.iterator() as iterator:
                async for message in iterator:
                    try:
                        await process_with_retries(
                            message,
                            handler=process_drop_started,
                            topology=topology,
                            config=ReliabilityConfig(),
                        )
                    except asyncio.CancelledError:
                        raise
                    except Exception:
                        logger.exception("Failed to process drop event")


async def run_consumer_forever(
    *,
    consumer: Callable[[], Awaitable[None]] = run_consumer,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> None:
    """Keep retrying initial broker connections without restarting the container."""
    await run_forever(
        consumer,
        initial_delay=INITIAL_RECONNECT_DELAY_SECONDS,
        max_delay=MAX_RECONNECT_DELAY_SECONDS,
        sleep=sleep,
        jitter=lambda: 0.5,
        label="Wishlist consumer",
    )


async def run() -> None:
    try:
        await run_consumer_forever()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
