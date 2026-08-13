"""Reconnect loops that do not churn Docker containers."""

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)


async def run_forever(
    runner: Callable[[], Awaitable[None]],
    *,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    jitter: Callable[[], float] = random.random,
    label: str = "RabbitMQ worker",
) -> None:
    """Retry startup failures and unexpected clean returns until cancelled."""
    delay = initial_delay
    while True:
        try:
            await runner()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("%s failed; reconnecting", label)
        else:
            logger.warning("%s stopped unexpectedly; reconnecting", label)
        actual_delay = delay * (0.75 + 0.5 * jitter())
        await sleep(actual_delay)
        delay = min(max_delay, delay * 2)
