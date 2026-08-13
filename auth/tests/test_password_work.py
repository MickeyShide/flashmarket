"""Capacity protection for Argon2 operations."""

import asyncio
import threading
import time

import pytest
from fastapi import status

from auth_service.api.error_handlers import ERROR_STATUS
from auth_service.application.errors import AuthCapacityExhausted
from auth_service.password_work import PasswordWorkGate


def test_capacity_exhaustion_maps_to_service_unavailable() -> None:
    assert ERROR_STATUS[AuthCapacityExhausted] == status.HTTP_503_SERVICE_UNAVAILABLE


async def test_password_gate_limits_thread_concurrency() -> None:
    gate = PasswordWorkGate(concurrency=2, acquire_timeout_seconds=1)
    lock = threading.Lock()
    active = 0
    maximum = 0

    def work() -> None:
        nonlocal active, maximum
        with lock:
            active += 1
            maximum = max(maximum, active)
        time.sleep(0.03)
        with lock:
            active -= 1

    await asyncio.gather(*(gate.run(work) for _ in range(6)))
    assert maximum == 2


async def test_password_gate_times_out_and_releases_after_failure() -> None:
    gate = PasswordWorkGate(concurrency=1, acquire_timeout_seconds=0.01)
    started = threading.Event()
    release = threading.Event()

    def blocking() -> None:
        started.set()
        release.wait(timeout=1)

    first = asyncio.create_task(gate.run(blocking))
    await asyncio.to_thread(started.wait, 1)
    with pytest.raises(AuthCapacityExhausted):
        await gate.run(lambda: None)
    release.set()
    await first

    def fail() -> None:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        await gate.run(fail)
    await gate.run(lambda: None)


async def test_password_gate_releases_after_cancellation() -> None:
    gate = PasswordWorkGate(concurrency=1, acquire_timeout_seconds=1)
    started = threading.Event()
    release = threading.Event()

    def blocking() -> None:
        started.set()
        release.wait(timeout=1)

    task = asyncio.create_task(gate.run(blocking))
    await asyncio.to_thread(started.wait, 1)
    task.cancel()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    await gate.run(lambda: None)
