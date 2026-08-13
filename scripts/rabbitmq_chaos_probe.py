"""Confirmed publish/load probe that must survive one RabbitMQ restart."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import time
import uuid

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message


def _expected_disconnect_handler(
    loop: asyncio.AbstractEventLoop,
    context: dict[str, object],
) -> None:
    """Keep expected broker-restart noise from looking like a probe failure."""
    exception = context.get("exception")
    module = type(exception).__module__ if exception is not None else ""
    if module.startswith(("aiormq", "pamqp")):
        return
    loop.default_exception_handler(context)


async def run(url: str, total: int, rate: float) -> None:
    asyncio.get_running_loop().set_exception_handler(_expected_disconnect_handler)
    for logger_name in ("aio_pika", "aiormq", "pamqp"):
        logger = logging.getLogger(logger_name)
        logger.disabled = True
    suffix = uuid.uuid4().hex
    exchange_name = f"flashmarket.chaos.{suffix}"
    queue_name = f"flashmarket.chaos.{suffix}"
    connection = await aio_pika.connect_robust(url, timeout=10)
    try:
        channel = await connection.channel(
            publisher_confirms=True, on_return_raises=True
        )
        exchange = await channel.declare_exchange(
            exchange_name, ExchangeType.DIRECT, durable=True, auto_delete=True
        )
        queue = await channel.declare_queue(queue_name, durable=True, auto_delete=True)
        await queue.bind(exchange, queue_name)
        print("READY", flush=True)
        for index in range(total):
            deadline = time.monotonic() + 60
            while True:
                try:
                    await exchange.publish(
                        Message(
                            str(index).encode(),
                            message_id=f"{suffix}-{index}",
                            delivery_mode=DeliveryMode.PERSISTENT,
                        ),
                        routing_key=queue_name,
                        mandatory=True,
                        timeout=5,
                    )
                    break
                except asyncio.CancelledError:
                    raise
                except Exception:
                    if time.monotonic() >= deadline:
                        raise
                    await asyncio.sleep(0.5)
            await asyncio.sleep(1 / rate)

        received: set[str] = set()
        delivery_count = 0
        deadline = time.monotonic() + 60
        while len(received) < total and time.monotonic() < deadline:
            message = await queue.get(no_ack=False, fail=False, timeout=1)
            if message is None:
                continue
            delivery_count += 1
            if message.message_id is not None:
                received.add(message.message_id)
            await message.ack()
        if len(received) != total:
            raise RuntimeError(
                f"received {len(received)} of {total} confirmed messages"
            )
        duplicates = delivery_count - len(received)
        print(
            f"PASS: {total} unique confirmed messages survived "
            f"({duplicates} duplicate deliveries)",
            flush=True,
        )
    finally:
        await connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.getenv("RABBITMQ_TEST_URL"))
    parser.add_argument("--total", type=int, default=100)
    parser.add_argument("--rate", type=float, default=20.0)
    args = parser.parse_args()
    if not args.url:
        parser.error("RABBITMQ_TEST_URL or --url is required")
    if args.total <= 0 or args.rate <= 0:
        parser.error("--total and --rate must be positive")
    asyncio.run(run(args.url, args.total, args.rate))


if __name__ == "__main__":
    main()
