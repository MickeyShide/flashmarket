"""Connection lifecycle tests for the Wishlist RabbitMQ consumer."""

import asyncio

import pytest

from wishlist.event_consumer import run_consumer_forever


@pytest.mark.asyncio
async def test_initial_connection_failures_retry_without_process_exit() -> None:
    attempts = 0
    delays: list[float] = []

    async def failing_consumer() -> None:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionError("RabbitMQ is unavailable")
        raise asyncio.CancelledError

    async def record_sleep(delay: float) -> None:
        delays.append(delay)

    with pytest.raises(asyncio.CancelledError):
        await run_consumer_forever(consumer=failing_consumer, sleep=record_sleep)

    assert attempts == 3
    assert delays == [1.0, 2.0]


@pytest.mark.asyncio
async def test_clean_consumer_exit_is_retried_with_backoff() -> None:
    attempts = 0
    delays: list[float] = []

    async def stopping_consumer() -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 3:
            raise asyncio.CancelledError

    async def record_sleep(delay: float) -> None:
        delays.append(delay)

    with pytest.raises(asyncio.CancelledError):
        await run_consumer_forever(consumer=stopping_consumer, sleep=record_sleep)

    assert delays == [1.0, 2.0]
