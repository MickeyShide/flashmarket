"""Regression test for media ValidationGate semaphore permit leak fix (BUG-006)."""

import asyncio

import pytest

from media_service.application.validation_gate import ValidationGate
from media_service.domain.exceptions import MediaCapacityExhausted


@pytest.mark.asyncio
async def test_validation_gate_no_permit_leak_on_timeout() -> None:
    """BUG-006: ValidationGate does not leak semaphore permit when acquisition times out."""
    gate = ValidationGate(concurrency=1, acquire_timeout_seconds=0.01)

    async def slow_operation() -> str:
        await asyncio.sleep(0.1)
        return "done"

    # Task 1 holds the only permit
    task1 = asyncio.create_task(gate.run(slow_operation))
    await asyncio.sleep(0.01)

    # Task 2 attempts to acquire and times out
    async def op2() -> str:
        return "op2"

    with pytest.raises(MediaCapacityExhausted):
        await gate.run(op2)

    # Await task 1 to finish and release
    await task1

    # Now semaphore must have permit available again (value == 1)
    assert gate._semaphore._value == 1

    # Task 3 should succeed immediately
    res = await gate.run(lambda: asyncio.sleep(0, result="success"))
    assert res == "success"
