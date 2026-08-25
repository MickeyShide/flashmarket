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
    begin_event_once,
    declare_consumer_topology,
    decode_json_object,
    delivery_identity,
    original_routing_key,
    periodic_heartbeat,
    process_with_retries,
    run_forever,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from payments.application.receipts import snapshot_from_order_event
from payments.application.services.payment import PaymentService
from payments.config import get_settings
from payments.domain.entities import PaymentStatus, ReceiptStatus
from payments.infrastructure.database import SessionFactory, engine
from payments.infrastructure.models import PaymentModel, PaymentReceiptModel, ProcessedEventModel
from payments.infrastructure.providers import (
    close_shared_payment_provider,
    get_shared_payment_provider,
)
from payments.infrastructure.repositories.payment import (
    OutboxRepository,
    PaymentReceiptRepository,
    PaymentRepository,
)

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
        provider=get_settings().payment_provider,
        status=PaymentStatus.PENDING,
        expires_at=expires_at,
    )
    await payment_repo.create(payment)
    snapshot = snapshot_from_order_event(payload)
    snapshot_json = snapshot.canonical_json()
    await PaymentReceiptRepository(session).create(
        PaymentReceiptModel(
            payment_id=payment.id,
            snapshot=snapshot_json,
            snapshot_hash=snapshot.content_hash(),
            status=(ReceiptStatus.SIMULATED if snapshot.customer else ReceiptStatus.NEEDS_CONTACT),
            error_code=None if snapshot.customer else "customer_contact_missing",
        )
    )
    logger.info("Created payment %s for order %s", payment.id, order_id)


async def handle_payment_refund_requested(
    session: AsyncSession,
    payload: dict[str, Any],
) -> None:
    """Refund payment when cancelled order receives payment."""
    payment_id = payload.get("payment_id")
    order_id = payload.get("order_id")
    payment_repo = PaymentRepository(session)
    payment = None
    if payment_id:
        payment = await payment_repo.get_by_id_for_update(uuid.UUID(str(payment_id)))
    elif order_id:
        payment = await payment_repo.get_by_order_id_for_update(uuid.UUID(str(order_id)))

    if payment is None:
        logger.warning("No payment found to refund for payload %s", payload)
        return
    settings = get_settings()
    service = PaymentService(
        session=session,
        payment_repo=payment_repo,
        outbox_repo=OutboxRepository(session),
        provider=get_shared_payment_provider(),
        provider_name=settings.payment_provider,
        return_url=settings.yookassa_return_url or "http://localhost/payment/return",
        test_mode_required=settings.yookassa_test_mode_required,
    )
    payment = await service.refund_payment(
        payment.id,
        reason=str(payload.get("reason", "order_cancelled_compensation")),
        commit=False,
    )
    logger.info(
        "Refund status %s for payment %s and cancelled order %s",
        payment.refund_status,
        payment.id,
        payment.order_id,
    )


HANDLERS: dict[str, Handler] = {
    "orders.PaymentRequested": handle_payment_requested,
    "orders.PaymentRefundRequested": handle_payment_refund_requested,
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
        async with session_factory() as session:
            if not await begin_event_once(
                session,
                ProcessedEventModel,
                event_id=delivery_identity(message, routing_key),
                routing_key=routing_key,
            ):
                logger.info("Skipping duplicate event %s", delivery_identity(message, routing_key))
                return
            await handler(session, body)
            if session.in_transaction():
                await session.commit()
    except (KeyError, TypeError, ValueError) as exc:
        raise PermanentMessageError("invalid payments event payload") from exc


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
            queue_name="payments.events",
            topic_exchange=exchange,
            routing_keys=("orders.PaymentRequested", "orders.PaymentRefundRequested"),
            config=reliability,
        )
        async with periodic_heartbeat(
            "/tmp/flashmarket-heartbeat.json",
            interval_seconds=settings.worker_heartbeat_interval_seconds,
            phase="payments_consumer",
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


async def run_reconciliation_loop() -> None:
    """Continuously reconcile durable uncertain provider operations."""
    settings = get_settings()
    provider = get_shared_payment_provider()
    while True:
        try:
            async with SessionFactory() as session:
                service = PaymentService(
                    session=session,
                    payment_repo=PaymentRepository(session),
                    outbox_repo=OutboxRepository(session),
                    provider=provider,
                    provider_name=settings.payment_provider,
                    return_url=(settings.yookassa_return_url or "http://localhost/payment/return"),
                    test_mode_required=settings.yookassa_test_mode_required,
                    webhook_max_attempts=settings.webhook_max_attempts,
                    attempt_ttl_seconds=settings.payment_attempt_ttl_seconds,
                )
                operations_processed = await service.reconcile_unknown_operations(
                    limit=settings.reconciliation_batch_size
                )
                webhooks_processed = await service.process_webhook_inbox(
                    limit=settings.webhook_batch_size
                )
                refunds_processed = await service.reconcile_refunds(
                    limit=settings.reconciliation_batch_size
                )
                if operations_processed or webhooks_processed or refunds_processed:
                    logger.info(
                        "Reconciliation batch completed: operations=%s webhooks=%s refunds=%s",
                        operations_processed,
                        webhooks_processed,
                        refunds_processed,
                    )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Payments reconciliation batch failed")
        await asyncio.sleep(settings.reconciliation_poll_interval_seconds)


async def run() -> None:
    """Start the consumer coroutine."""
    try:
        settings = get_settings()
        async with asyncio.TaskGroup() as tasks:
            tasks.create_task(
                run_forever(
                    run_consumer,
                    initial_delay=settings.rabbitmq_reconnect_initial_seconds,
                    max_delay=settings.rabbitmq_reconnect_max_seconds,
                    label="Payments consumer",
                )
            )
            tasks.create_task(run_reconciliation_loop())
    finally:
        await close_shared_payment_provider()
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
