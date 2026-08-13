"""Capacity protection for upload validation."""

import asyncio

import pytest
from fastapi import status

from media_service.api.error_handlers import ERROR_STATUS
from media_service.application.validation_gate import ValidationGate
from media_service.domain.exceptions import MediaCapacityExhausted


def test_capacity_exhaustion_maps_to_service_unavailable() -> None:
    assert ERROR_STATUS[MediaCapacityExhausted] == status.HTTP_503_SERVICE_UNAVAILABLE


async def test_validation_gate_limits_concurrency() -> None:
    gate = ValidationGate(concurrency=2, acquire_timeout_seconds=1)
    active = 0
    maximum = 0

    async def work() -> None:
        nonlocal active, maximum
        active += 1
        maximum = max(maximum, active)
        await asyncio.sleep(0.02)
        active -= 1

    await asyncio.gather(*(gate.run(work) for _ in range(6)))
    assert maximum == 2


async def test_validation_gate_times_out_and_releases_after_failure() -> None:
    gate = ValidationGate(concurrency=1, acquire_timeout_seconds=0.01)
    release = asyncio.Event()
    first = asyncio.create_task(gate.run(release.wait))
    await asyncio.sleep(0)

    with pytest.raises(MediaCapacityExhausted):
        await gate.run(lambda: asyncio.sleep(0))
    release.set()
    await first

    async def fail() -> None:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        await gate.run(fail)
    await gate.run(lambda: asyncio.sleep(0))


async def test_validation_gate_releases_after_cancellation() -> None:
    gate = ValidationGate(concurrency=1, acquire_timeout_seconds=1)
    operation_started = asyncio.Event()

    async def blocking() -> None:
        operation_started.set()
        await asyncio.Event().wait()

    task = asyncio.create_task(gate.run(blocking))
    await operation_started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await gate.run(lambda: asyncio.sleep(0))
