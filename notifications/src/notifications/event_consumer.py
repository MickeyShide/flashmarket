"""Inbound RabbitMQ consumer for notifications service."""

from __future__ import annotations

import asyncio
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
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from notifications.config import get_settings
from notifications.domain.entities import NotificationChannel, NotificationStatus
from notifications.infrastructure.database import SessionFactory, engine
from notifications.infrastructure.models import NotificationModel, ProcessedEventModel
from notifications.infrastructure.repositories.notification import (
    NotificationRepository,
)

logger = logging.getLogger(__name__)

Handler = Callable[[AsyncSession, dict[str, Any]], Awaitable[None]]


async def _create_notification(
    session: AsyncSession,
    user_id: uuid.UUID,
    subject: str,
    body: str,
    recipient: str | None = None,
    channel: NotificationChannel = NotificationChannel.EMAIL,
    event_key: str | None = None,
) -> None:
    """Persist a pending notification."""
    repo = NotificationRepository(session)
    notification = NotificationModel(
        user_id=user_id,
        channel=channel,
        subject=subject,
        body=body,
        recipient=recipient or f"{user_id}@example.com",
        status=NotificationStatus.PENDING,
        event_key=event_key,
    )
    try:
        await repo.create(notification)
        logger.info("Created notification %s for user %s", notification.id, user_id)
    except IntegrityError:
        logger.info("Notification with event_key %s already exists, skipping", event_key)


async def handle_order_created(
    session: AsyncSession,
    payload: dict[str, Any],
) -> None:
    """Notify user that order was created."""
    user_id = uuid.UUID(str(payload["user_id"]))
    order_id = str(payload.get("order_id", ""))
    subject = "Order created"
    body = f"Your order {order_id} has been created and is awaiting payment."
    event_key = f"order:{order_id}:created"

    existing = await session.scalar(
        select(NotificationModel).where(
            NotificationModel.event_key == event_key,
        )
    )
    if existing is not None:
        logger.info("Notification for %s (order %s) already exists, skipping", subject, order_id)
        return

    await _create_notification(session, user_id, subject=subject, body=body, event_key=event_key)


async def handle_order_confirmed(
    session: AsyncSession,
    payload: dict[str, Any],
) -> None:
    """Notify user that order was confirmed."""
    user_id = uuid.UUID(str(payload["user_id"]))
    order_id = str(payload.get("order_id", ""))
    subject = "Order confirmed"
    body = f"Your order {order_id} has been confirmed."
    event_key = f"order:{order_id}:confirmed"

    existing = await session.scalar(
        select(NotificationModel).where(
            NotificationModel.event_key == event_key,
        )
    )
    if existing is not None:
        logger.info("Notification for %s (order %s) already exists, skipping", subject, order_id)
        return

    await _create_notification(session, user_id, subject=subject, body=body, event_key=event_key)


async def handle_order_cancelled(
    session: AsyncSession,
    payload: dict[str, Any],
) -> None:
    """Notify user that order was cancelled."""
    user_id = uuid.UUID(str(payload["user_id"]))
    order_id = str(payload.get("order_id", ""))
    reason = str(payload.get("reason", ""))
    subject = "Order cancelled"
    body = f"Your order {order_id} was cancelled. Reason: {reason or 'unknown'}."
    event_key = f"order:{order_id}:cancelled"

    existing = await session.scalar(
        select(NotificationModel).where(
            NotificationModel.event_key == event_key,
        )
    )
    if existing is not None:
        logger.info("Notification for %s (order %s) already exists, skipping", subject, order_id)
        return

    await _create_notification(session, user_id, subject=subject, body=body, event_key=event_key)


async def handle_wishlist_drop_available(
    session: AsyncSession,
    payload: dict[str, Any],
) -> None:
    """Notify a user that a drop containing a wished product has started."""
    user_id = uuid.UUID(str(payload["user_id"]))
    event_key = str(payload["event_key"])
    existing = await session.scalar(
        select(NotificationModel).where(NotificationModel.event_key == event_key)
    )
    if existing is not None:
        return

    drop_name = str(payload.get("drop_name") or "Flash drop")
    await _create_notification(
        session,
        user_id,
        subject="Wishlist item is available",
        body=f"{drop_name} has started. An item from your wishlist is available now.",
        channel=NotificationChannel.DROP_ALERT,
        event_key=event_key,
    )


HANDLERS: dict[str, Handler] = {
    "orders.OrderCreated": handle_order_created,
    "orders.OrderConfirmed": handle_order_confirmed,
    "orders.OrderCancelled": handle_order_cancelled,
    "wishlist.DropAvailable": handle_wishlist_drop_available,
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
        raise PermanentMessageError("invalid notifications event payload") from exc


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
            queue_name="notifications.events",
            topic_exchange=exchange,
            routing_keys=tuple(HANDLERS),
            config=reliability,
        )
        async with periodic_heartbeat(
            "/tmp/flashmarket-heartbeat.json",
            interval_seconds=settings.worker_heartbeat_interval_seconds,
            phase="notifications_consumer",
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
            label="Notifications consumer",
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
