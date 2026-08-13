"""Declare additive retry and dead-letter topology around an existing queue."""

from dataclasses import dataclass

from aio_pika import ExchangeType
from aio_pika.abc import AbstractChannel, AbstractExchange, AbstractQueue

from rabbitmq_reliability.config import ReliabilityConfig

RETRY_EXCHANGE = "flashmarket.retry"
DEAD_LETTER_EXCHANGE = "flashmarket.dead-letter"


@dataclass(frozen=True, slots=True)
class ConsumerTopology:
    queue: AbstractQueue
    retry_exchange: AbstractExchange
    dead_letter_exchange: AbstractExchange
    retry_queue_names: tuple[str, str, str]
    dlq_name: str


async def declare_consumer_topology(
    channel: AbstractChannel,
    *,
    queue_name: str,
    topic_exchange: AbstractExchange,
    routing_keys: tuple[str, ...],
    config: ReliabilityConfig,
) -> ConsumerTopology:
    """Declare a main queue plus additive per-consumer retry and DLQ queues."""
    retry_exchange = await channel.declare_exchange(
        RETRY_EXCHANGE, ExchangeType.DIRECT, durable=True
    )
    dead_letter_exchange = await channel.declare_exchange(
        DEAD_LETTER_EXCHANGE, ExchangeType.DIRECT, durable=True
    )
    main_queue = await channel.declare_queue(queue_name, durable=True)
    for routing_key in routing_keys:
        await main_queue.bind(topic_exchange, routing_key=routing_key)
    await main_queue.bind(retry_exchange, routing_key=queue_name)

    dlq_name = f"{queue_name}.dlq"
    dlq = await channel.declare_queue(dlq_name, durable=True)
    await dlq.bind(dead_letter_exchange, routing_key=dlq_name)

    retry_names: list[str] = []
    for attempt, delay in enumerate(config.retry_delays_seconds, start=1):
        retry_name = f"{queue_name}.retry.{attempt}"
        retry_queue = await channel.declare_queue(
            retry_name,
            durable=True,
            arguments={
                "x-message-ttl": delay * 1000,
                "x-dead-letter-exchange": RETRY_EXCHANGE,
                "x-dead-letter-routing-key": queue_name,
            },
        )
        await retry_queue.bind(retry_exchange, routing_key=retry_name)
        retry_names.append(retry_name)

    return ConsumerTopology(
        queue=main_queue,
        retry_exchange=retry_exchange,
        dead_letter_exchange=dead_letter_exchange,
        retry_queue_names=(retry_names[0], retry_names[1], retry_names[2]),
        dlq_name=dlq_name,
    )
