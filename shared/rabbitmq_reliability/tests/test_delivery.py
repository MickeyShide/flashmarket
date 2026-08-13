from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from rabbitmq_reliability import (
    ConsumerTopology,
    PermanentMessageError,
    ReliabilityConfig,
    process_with_retries,
)


def message(*, attempt: int = 0):
    headers = {"x-flashmarket-attempt": attempt} if attempt else {}
    return SimpleNamespace(
        body=b'{"ok":true}',
        headers=headers,
        routing_key="orders.PaymentRequested",
        content_type="application/json",
        content_encoding=None,
        delivery_mode=2,
        priority=None,
        correlation_id="corr",
        reply_to=None,
        message_id="event-1",
        timestamp=None,
        type="PaymentRequested",
        user_id=None,
        app_id=None,
        ack=AsyncMock(),
        reject=AsyncMock(),
    )


def topology():
    return ConsumerTopology(
        queue=SimpleNamespace(),
        retry_exchange=SimpleNamespace(publish=AsyncMock(return_value=True)),
        dead_letter_exchange=SimpleNamespace(publish=AsyncMock(return_value=True)),
        retry_queue_names=("q.retry.1", "q.retry.2", "q.retry.3"),
        dlq_name="q.dlq",
    )


@pytest.mark.asyncio
async def test_success_acknowledges_original() -> None:
    incoming = message()
    topology_value = topology()
    await process_with_retries(
        incoming,
        handler=AsyncMock(return_value=None),
        topology=topology_value,
        config=ReliabilityConfig(),
    )
    incoming.ack.assert_awaited_once()
    topology_value.retry_exchange.publish.assert_not_awaited()


@pytest.mark.asyncio
async def test_transient_failure_moves_to_next_retry_before_ack() -> None:
    incoming = message(attempt=1)
    topology_value = topology()
    await process_with_retries(
        incoming,
        handler=AsyncMock(side_effect=ConnectionError("db down")),
        topology=topology_value,
        config=ReliabilityConfig(),
    )
    args, kwargs = topology_value.retry_exchange.publish.await_args
    assert kwargs["routing_key"] == "q.retry.2"
    assert kwargs["mandatory"] is True
    assert args[0].headers["x-flashmarket-attempt"] == 2
    incoming.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_permanent_failure_goes_directly_to_dlq() -> None:
    incoming = message()
    topology_value = topology()
    await process_with_retries(
        incoming,
        handler=AsyncMock(side_effect=PermanentMessageError("bad json")),
        topology=topology_value,
        config=ReliabilityConfig(),
    )
    assert topology_value.dead_letter_exchange.publish.await_args.kwargs["routing_key"] == "q.dlq"


@pytest.mark.asyncio
async def test_exhausted_failure_goes_to_dlq() -> None:
    incoming = message(attempt=3)
    topology_value = topology()
    await process_with_retries(
        incoming,
        handler=AsyncMock(side_effect=TimeoutError()),
        topology=topology_value,
        config=ReliabilityConfig(),
    )
    assert topology_value.dead_letter_exchange.publish.await_args.kwargs["routing_key"] == "q.dlq"


@pytest.mark.asyncio
async def test_move_failure_requeues_original_without_ack() -> None:
    incoming = message()
    topology_value = topology()
    topology_value.retry_exchange.publish.side_effect = TimeoutError()
    with pytest.raises(TimeoutError):
        await process_with_retries(
            incoming,
            handler=AsyncMock(side_effect=ConnectionError()),
            topology=topology_value,
            config=ReliabilityConfig(),
        )
    incoming.reject.assert_awaited_once_with(requeue=True)
    incoming.ack.assert_not_awaited()
