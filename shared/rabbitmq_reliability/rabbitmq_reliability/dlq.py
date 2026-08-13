"""Conservative command-line inspection and replay for FlashMarket DLQs."""

from __future__ import annotations

import argparse
import asyncio
import os
from collections.abc import Sequence

import aio_pika
from aio_pika import DeliveryMode, Message
from aio_pika.abc import AbstractExchange, AbstractIncomingMessage, AbstractQueue

from .delivery import ORIGINAL_ROUTING_KEY_HEADER, publish_confirmed


def _replay_copy(source: AbstractIncomingMessage) -> tuple[Message, str]:
    headers = dict(source.headers or {})
    routing_key_value = headers.get(ORIGINAL_ROUTING_KEY_HEADER, source.routing_key or "")
    routing_key = (
        routing_key_value.decode("utf-8", errors="strict")
        if isinstance(routing_key_value, bytes)
        else str(routing_key_value)
    )
    if not routing_key:
        raise ValueError("DLQ message has no original routing key")
    headers["x-flashmarket-replayed"] = True
    return (
        Message(
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
        ),
        routing_key,
    )


async def replay_queue(
    queue: AbstractQueue,
    exchange: AbstractExchange,
    *,
    limit: int,
    timeout_seconds: float = 5.0,
) -> int:
    """Replay at most ``limit`` messages, ACKing only publisher-confirmed copies."""
    replayed = 0
    for _ in range(limit):
        source = await queue.get(no_ack=False, fail=False, timeout=1)
        if source is None:
            break
        try:
            message, routing_key = _replay_copy(source)
            await publish_confirmed(
                exchange,
                message,
                routing_key,
                timeout_seconds=timeout_seconds,
                mandatory=True,
            )
        except asyncio.CancelledError:
            await source.reject(requeue=True)
            raise
        except Exception:
            await source.reject(requeue=True)
            raise
        await source.ack()
        replayed += 1
    return replayed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("queue", help="existing queue name; must end in .dlq")
    parser.add_argument("--url", default=os.getenv("RABBITMQ_URL"))
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status", help="print the current ready-message count")
    replay = subparsers.add_parser("replay", help="confirmed replay to the topic exchange")
    replay.add_argument("--exchange", default="flashmarket.events")
    replay.add_argument("--limit", type=int, required=True)
    replay.add_argument("--timeout", type=float, default=5.0)
    replay.add_argument(
        "--yes",
        action="store_true",
        help="required safety switch; without it replay is a dry run",
    )
    return parser


async def _run(args: argparse.Namespace) -> int:
    if not args.url:
        raise SystemExit("RABBITMQ_URL or --url is required")
    if not args.queue.endswith(".dlq"):
        raise SystemExit("refusing a non-DLQ queue name")
    connection = await aio_pika.connect(args.url, timeout=10)
    async with connection:
        channel = await connection.channel(publisher_confirms=True, on_return_raises=True)
        queue = await channel.declare_queue(args.queue, passive=True)
        count = queue.declaration_result.message_count
        if args.command == "status" or not args.yes:
            action = "would replay" if args.command == "replay" else "ready"
            amount = min(count, args.limit) if args.command == "replay" else count
            print(f"{args.queue}: {action} {amount} message(s)")
            return 0
        if args.limit <= 0:
            raise SystemExit("--limit must be positive")
        exchange = await channel.get_exchange(args.exchange, ensure=True)
        replayed = await replay_queue(
            queue,
            exchange,
            limit=args.limit,
            timeout_seconds=args.timeout,
        )
        print(f"{args.queue}: replayed {replayed} message(s)")
    return 0


def main(argv: Sequence[str] | None = None) -> None:
    raise SystemExit(asyncio.run(_run(_parser().parse_args(argv))))


if __name__ == "__main__":
    main()
