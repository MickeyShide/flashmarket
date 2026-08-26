"""Transactional outbox relay to RabbitMQ."""

from __future__ import annotations

import asyncio
import logging

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message
from aio_pika.abc import AbstractExchange
from rabbitmq_reliability import (
    claim_outbox_event,
    observe_outbox_age,
    publish_confirmed,
    record_outbox_result,
    run_forever,
    touch_heartbeat,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from notifications.application.services.notification import NotificationService
from notifications.config import get_settings, utc_now
from notifications.domain.entities import NotificationEventType
from notifications.infrastructure.database import SessionFactory, engine
from notifications.infrastructure.models import OutboxEventModel
from notifications.infrastructure.repositories.notification import (
    NotificationRepository,
    OutboxRepository,
)

logger = logging.getLogger(__name__)


EVENT_ROUTING_KEYS: dict[str, str] = {
    NotificationEventType.NOTIFICATION_SENT: "notifications.NotificationSent",
}


async def publish_outbox_batch(
    exchange: AbstractExchange,
    *,
    session_factory: async_sessionmaker[AsyncSession] = SessionFactory,
) -> int:
    """Publish one batch of pending outbox events."""
    settings = get_settings()
    processed = 0
    for _ in range(settings.outbox_batch_size):
        claimed = await claim_outbox_event(
            session_factory,
            OutboxEventModel,
            utc_now(),
            lease_seconds=settings.outbox_claim_lease_seconds,
        )
        if claimed is None:
            break
        event, token = claimed
        error: Exception | None = None
        try:
            routing_key = EVENT_ROUTING_KEYS.get(
                event.event_type,
                f"notifications.{event.event_type}",
            )
            await publish_confirmed(
                exchange,
                Message(
                    body=event.payload.encode("utf-8"),
                    content_type="application/json",
                    delivery_mode=DeliveryMode.PERSISTENT,
                    message_id=str(event.id),
                    type=event.event_type,
                    timestamp=event.created_at,
                    headers={"event_id": str(event.id)},
                ),
                routing_key,
                timeout_seconds=settings.rabbitmq_publish_timeout_seconds,
                mandatory=False,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            error = exc
            logger.warning("Failed to publish outbox event %s: %s", event.id, exc)
        await record_outbox_result(
            session_factory,
            OutboxEventModel,
            event.id,
            token,
            utc_now(),
            error,
            max_backoff_seconds=settings.outbox_max_backoff_seconds,
        )
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
                async with SessionFactory() as session:
                    service = NotificationService(
                        session=session,
                        notification_repo=NotificationRepository(session),
                        outbox_repo=OutboxRepository(session),
                    )
                    await service.deliver_pending_notifications()
                processed = await publish_outbox_batch(exchange)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Outbox batch failed")
                await asyncio.sleep(settings.outbox_poll_interval_seconds)
                continue
            if processed:
                logger.info("Processed %d outbox event(s)", processed)
            await observe_outbox_age(SessionFactory, OutboxEventModel, utc_now(), "notifications")
            touch_heartbeat("/tmp/flashmarket-heartbeat.json", "notifications_outbox")
            await asyncio.sleep(settings.outbox_poll_interval_seconds)


async def run_worker() -> None:
    """Reconnect the outbox worker after broker failures."""
    settings = get_settings()
    await run_forever(
        run_connected_worker,
        initial_delay=settings.rabbitmq_reconnect_initial_seconds,
        max_delay=settings.rabbitmq_reconnect_max_seconds,
        label="Notifications outbox",
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
