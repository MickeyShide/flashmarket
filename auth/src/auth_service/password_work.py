"""Bound concurrent memory-intensive password operations."""

import asyncio
from collections.abc import Callable
from functools import lru_cache
from typing import TypeVar

from anyio import to_thread

from auth_service.application.errors import AuthCapacityExhausted
from auth_service.config import get_settings

T = TypeVar("T")


class PasswordWorkGate:
    """Limit the number of Argon2 jobs admitted by this process."""

    def __init__(self, concurrency: int, acquire_timeout_seconds: float) -> None:
        self._semaphore = asyncio.Semaphore(concurrency)
        self._acquire_timeout_seconds = acquire_timeout_seconds

    async def run(self, function: Callable[..., T], *args: object, **kwargs: object) -> T:
        try:
            async with asyncio.timeout(self._acquire_timeout_seconds):
                await self._semaphore.acquire()
        except TimeoutError as exc:
            raise AuthCapacityExhausted from exc
        try:
            return await to_thread.run_sync(lambda: function(*args, **kwargs))
        finally:
            self._semaphore.release()


@lru_cache
def get_password_work_gate() -> PasswordWorkGate:
    settings = get_settings()
    return PasswordWorkGate(
        settings.password_work_concurrency,
        settings.password_work_acquire_timeout_seconds,
    )


async def run_password_work[T](
    function: Callable[..., T], *args: object, **kwargs: object
) -> T:
    """Execute one password function after acquiring bounded capacity."""
    return await get_password_work_gate().run(function, *args, **kwargs)
