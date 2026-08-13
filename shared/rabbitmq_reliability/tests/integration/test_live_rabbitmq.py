"""Live RabbitMQ delivery guarantees; run only with RABBITMQ_TEST_URL set."""

from __future__ import annotations

import os
import uuid

import aio_pika
import pytest
from aio_pika import ExchangeType, Message
from aio_pika.exceptions import DeliveryError

from rabbitmq_reliability import (
    PermanentMessageError,
    ReliabilityConfig,
    declare_consumer_topology,
    process_with_retries,
    publish_confirmed,
)
from rabbitmq_reliability.dlq import replay_queue

pytestmark = pytest.mark.integration
RABBITMQ_URL = os.getenv("RABBITMQ_TEST_URL")


@pytest.fixture
async def live_channel():
    if not RABBITMQ_URL:
        pytest.skip("RABBITMQ_TEST_URL is not set")
    connection = await aio_pika.connect(RABBITMQ_URL, timeout=10)
    channel = await connection.channel(publisher_confirms=True, on_return_raises=True)
    try:
        yield channel
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_confirmed_retry_dlq_and_replay_round_trip(live_channel) -> None:
    suffix = uuid.uuid4().hex
    exchange = await live_channel.declare_exchange(
        f"test.events.{suffix}", ExchangeType.TOPIC, auto_delete=True
    )
    config = ReliabilityConfig(retry_delays_seconds=(1, 2, 3))
    topology = await declare_consumer_topology(
        live_channel,
        queue_name=f"test.{suffix}",
        topic_exchange=exchange,
        routing_keys=("test.event",),
        config=config,
    )
    await publish_confirmed(
        exchange,
        Message(b'{"event_id":"live-1"}', message_id="live-1"),
        "test.event",
        timeout_seconds=5,
    )
    incoming = await topology.queue.get(no_ack=False, fail=True, timeout=5)

    async def invalid(_message) -> None:
        raise PermanentMessageError("poison payload")

    await process_with_retries(
        incoming,
        handler=invalid,
        topology=topology,
        config=config,
    )
    dlq = await live_channel.get_queue(topology.dlq_name, ensure=True)
    assert await replay_queue(dlq, exchange, limit=1) == 1
    replayed = await topology.queue.get(no_ack=False, fail=True, timeout=5)
    assert replayed.message_id == "live-1"
    assert replayed.headers["x-flashmarket-replayed"] is True
    await replayed.ack()


@pytest.mark.asyncio
async def test_unroutable_mandatory_publication_fails(live_channel) -> None:
    exchange = await live_channel.declare_exchange(
        f"test.unroutable.{uuid.uuid4().hex}", ExchangeType.TOPIC, auto_delete=True
    )
    with pytest.raises(DeliveryError):
        await publish_confirmed(
            exchange,
            Message(b"unroutable"),
            "missing.route",
            timeout_seconds=5,
            mandatory=True,
        )
