"""At-least-once consumer and publisher primitives."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any

from aio_pika import DeliveryMode, Message
from aio_pika.abc import AbstractExchange, AbstractIncomingMessage
from pamqp import commands

from rabbitmq_reliability.config import ReliabilityConfig
from rabbitmq_reliability.metrics import CONSUMER_MOVES, PUBLISH_OUTCOMES
from rabbitmq_reliability.topology import ConsumerTopology

ATTEMPT_HEADER = "x-flashmarket-attempt"
ORIGINAL_ROUTING_KEY_HEADER = "x-flashmarket-original-routing-key"
FAILURE_KIND_HEADER = "x-flashmarket-failure-kind"
LAST_ERROR_HEADER = "x-flashmarket-last-error"


class PermanentMessageError(ValueError):
    """A message cannot become valid by retrying later."""


def decode_json_object(message: AbstractIncomingMessage) -> dict[str, Any]:
    """Decode a JSON object and classify malformed payloads as permanent."""
    try:
        payload = json.loads(message.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PermanentMessageError("message body is not valid UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise PermanentMessageError("message body must be a JSON object")
    return payload


def sanitize_error(error: BaseException, limit: int = 1000) -> str:
    value = " ".join(str(error).split()) or error.__class__.__name__
    return value[:limit]


def retry_attempt(message: AbstractIncomingMessage) -> int:
    raw = (getattr(message, "headers", None) or {}).get(ATTEMPT_HEADER, 0)
    if not isinstance(raw, (bytes, bytearray, float, int, str)):
        return 0
    try:
        return max(0, min(3, int(raw)))
    except (TypeError, ValueError):
        return 0


def original_routing_key(message: AbstractIncomingMessage) -> str:
    raw = (getattr(message, "headers", None) or {}).get(ORIGINAL_ROUTING_KEY_HEADER)
    return str(raw) if isinstance(raw, (bytes, str)) else (message.routing_key or "")


def copy_message(
    source: AbstractIncomingMessage,
    *,
    attempt: int,
    failure_kind: str,
    error: BaseException,
) -> Message:
    headers = dict(source.headers or {})
    headers.update(
        {
            ATTEMPT_HEADER: attempt,
            ORIGINAL_ROUTING_KEY_HEADER: headers.get(
                ORIGINAL_ROUTING_KEY_HEADER, source.routing_key or ""
            ),
            FAILURE_KIND_HEADER: failure_kind,
            LAST_ERROR_HEADER: sanitize_error(error),
        }
    )
    return Message(
        body=source.body,
        headers=headers,
        content_type=source.content_type,
        content_encoding=source.content_encoding,
        delivery_mode=source.delivery_mode or DeliveryMode.PERSISTENT,
        priority=source.priority,
        correlation_id=source.correlation_id,
        reply_to=source.reply_to,
        message_id=source.message_id,
        timestamp=source.timestamp,
        type=source.type,
        user_id=source.user_id,
        app_id=source.app_id,
    )


async def publish_confirmed(
    exchange: AbstractExchange,
    message: Message,
    routing_key: str,
    *,
    timeout_seconds: float,
    mandatory: bool = True,
) -> None:
    try:
        async with asyncio.timeout(timeout_seconds):
            result = await exchange.publish(
                message,
                routing_key=routing_key,
                mandatory=mandatory,
            )
    except asyncio.CancelledError:
        raise
    except TimeoutError:
        PUBLISH_OUTCOMES.labels("timeout").inc()
        raise
    except Exception:
        PUBLISH_OUTCOMES.labels("error").inc()
        raise
    if result is None or isinstance(result, (commands.Basic.Nack, commands.Basic.Reject)):
        PUBLISH_OUTCOMES.labels("rejected").inc()
        raise RuntimeError("RabbitMQ rejected the publication")
    PUBLISH_OUTCOMES.labels("confirmed").inc()


async def process_with_retries(
    message: AbstractIncomingMessage,
    *,
    handler: Callable[[AbstractIncomingMessage], Awaitable[None]],
    topology: ConsumerTopology,
    config: ReliabilityConfig,
) -> None:
    """Run a handler and safely move a failed message before ACKing its source."""
    try:
        await handler(message)
    except asyncio.CancelledError:
        raise
    except Exception as error:
        permanent = isinstance(error, PermanentMessageError)
        current_attempt = retry_attempt(message)
        if permanent or current_attempt >= len(topology.retry_queue_names):
            destination = topology.dlq_name
            destination_exchange = topology.dead_letter_exchange
            next_attempt = current_attempt
            failure_kind = "permanent" if permanent else "retries_exhausted"
        else:
            next_attempt = current_attempt + 1
            destination = topology.retry_queue_names[current_attempt]
            destination_exchange = topology.retry_exchange
            failure_kind = "transient"
        failure_copy = copy_message(
            message,
            attempt=next_attempt,
            failure_kind=failure_kind,
            error=error,
        )
        try:
            await publish_confirmed(
                destination_exchange,
                failure_copy,
                destination,
                timeout_seconds=config.publish_timeout_seconds,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            await message.reject(requeue=True)
            raise
        await message.ack()
        CONSUMER_MOVES.labels("dlq" if destination == topology.dlq_name else "retry").inc()
        return
    await message.ack()
