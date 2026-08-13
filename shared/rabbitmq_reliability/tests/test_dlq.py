from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from rabbitmq_reliability.dlq import replay_queue


def incoming(routing_key: str = "orders.PaymentRequested") -> SimpleNamespace:
    return SimpleNamespace(
        body=b'{"event_id":"event-1"}',
        headers={"x-flashmarket-original-routing-key": routing_key},
        routing_key="orders.events.dlq",
        content_type="application/json",
        content_encoding=None,
        delivery_mode=2,
        priority=None,
        correlation_id=None,
        reply_to=None,
        message_id="event-1",
        timestamp=None,
        type="PaymentRequested",
        user_id=None,
        app_id="orders",
        ack=AsyncMock(),
        reject=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_replay_acknowledges_only_after_confirm() -> None:
    source = incoming()
    queue = SimpleNamespace(get=AsyncMock(side_effect=[source, None]))
    exchange = SimpleNamespace(publish=AsyncMock(return_value=True))
    count = await replay_queue(queue, exchange, limit=5)
    assert count == 1
    assert exchange.publish.await_args.kwargs["routing_key"] == "orders.PaymentRequested"
    assert exchange.publish.await_args.args[0].message_id == "event-1"
    source.ack.assert_awaited_once()
    source.reject.assert_not_awaited()


@pytest.mark.asyncio
async def test_replay_failure_requeues_source() -> None:
    source = incoming()
    queue = SimpleNamespace(get=AsyncMock(return_value=source))
    exchange = SimpleNamespace(publish=AsyncMock(side_effect=TimeoutError))
    with pytest.raises(TimeoutError):
        await replay_queue(queue, exchange, limit=1)
    source.reject.assert_awaited_once_with(requeue=True)
    source.ack.assert_not_awaited()
