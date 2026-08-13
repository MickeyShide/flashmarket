"""Translate drop starts into notifications for users watching its products."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from uuid import UUID

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message
from aio_pika.abc import AbstractIncomingMessage

from wishlist.config import get_settings
from wishlist.infrastructure.database import SessionFactory, engine
from wishlist.infrastructure.repositories.wishlist import WishlistRepository

logger = logging.getLogger(__name__)

INITIAL_RECONNECT_DELAY_SECONDS = 1.0
MAX_RECONNECT_DELAY_SECONDS = 30.0


async def process_drop_started(
    message: AbstractIncomingMessage,
    exchange: aio_pika.abc.AbstractExchange,
) -> None:
    async with message.process(reject_on_redelivered=False):
        payload = json.loads(message.body.decode("utf-8"))
        product_ids = [UUID(value) for value in payload.get("product_ids", [])]
        if not product_ids:
            return

        async with SessionFactory() as session:
            users = await WishlistRepository(session).get_users_for_products(product_ids)

        for user_id in users:
            notification = {
                "event_key": f"drop:{payload['drop_id']}:user:{user_id}",
                "user_id": str(user_id),
                "drop_id": str(payload["drop_id"]),
                "drop_name": str(payload.get("name") or "Flash drop"),
                "drop_slug": str(payload.get("slug") or ""),
            }
            await exchange.publish(
                Message(
                    json.dumps(notification, separators=(",", ":")).encode(),
                    content_type="application/json",
                    delivery_mode=DeliveryMode.PERSISTENT,
                ),
                routing_key="wishlist.DropAvailable",
            )
        logger.info("Published drop %s to %d wishlist users", payload["drop_id"], len(users))


async def run_consumer() -> None:
    settings = get_settings()
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=10)
        exchange = await channel.declare_exchange(
            settings.rabbitmq_exchange, ExchangeType.TOPIC, durable=True
        )
        queue = await channel.declare_queue("wishlist.drop-events", durable=True)
        await queue.bind(exchange, routing_key="drops.DropStarted")
        async with queue.iterator() as iterator:
            async for message in iterator:
                try:
                    await process_drop_started(message, exchange)
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
    retry_delay = INITIAL_RECONNECT_DELAY_SECONDS
    while True:
        try:
            await consumer()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(
                "Wishlist consumer connection failed; retrying in %.1f seconds",
                retry_delay,
            )
        else:
            logger.warning(
                "Wishlist consumer stopped without cancellation; retrying in %.1f seconds",
                retry_delay,
            )

        await sleep(retry_delay)
        retry_delay = min(MAX_RECONNECT_DELAY_SECONDS, retry_delay * 2)


async def run() -> None:
    try:
        await run_consumer_forever()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
