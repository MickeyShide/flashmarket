"""Bound concurrent object reads and image decodes."""

import asyncio
from collections.abc import Awaitable, Callable
from functools import lru_cache
from typing import TypeVar

from media_service.config import get_settings
from media_service.domain.exceptions import MediaCapacityExhausted

T = TypeVar("T")


class ValidationGate:
    """Limit memory-amplifying upload validation work in this process."""

    def __init__(self, concurrency: int, acquire_timeout_seconds: float) -> None:
        self._semaphore = asyncio.Semaphore(concurrency)
        self._acquire_timeout_seconds = acquire_timeout_seconds

    async def run(self, operation: Callable[[], Awaitable[T]]) -> T:
        try:
            async with asyncio.timeout(self._acquire_timeout_seconds):
                await self._semaphore.acquire()
        except TimeoutError as exc:
            raise MediaCapacityExhausted from exc
        try:
            return await operation()
        finally:
            self._semaphore.release()


@lru_cache
def get_validation_gate() -> ValidationGate:
    settings = get_settings()
    return ValidationGate(
        settings.validation_concurrency,
        settings.validation_acquire_timeout_seconds,
    )
