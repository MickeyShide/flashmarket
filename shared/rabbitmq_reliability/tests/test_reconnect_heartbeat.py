import asyncio
import json
import time

import pytest

from rabbitmq_reliability import heartbeat_is_fresh, run_forever, touch_heartbeat


@pytest.mark.asyncio
async def test_reconnect_retries_failures_and_clean_returns() -> None:
    calls = 0
    delays: list[float] = []

    async def runner() -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ConnectionError
        if calls == 3:
            raise asyncio.CancelledError

    async def sleep(delay: float) -> None:
        delays.append(delay)

    with pytest.raises(asyncio.CancelledError):
        await run_forever(runner, sleep=sleep, jitter=lambda: 0.5)
    assert calls == 3
    assert delays == [1.0, 2.0]


def test_heartbeat_freshness(tmp_path) -> None:
    path = tmp_path / "worker.json"
    touch_heartbeat(path, "connected")
    assert heartbeat_is_fresh(path, 10)
    path.write_text(json.dumps({"timestamp": time.time() - 20, "phase": "old"}))
    assert not heartbeat_is_fresh(path, 10)
    path.write_text("broken")
    assert not heartbeat_is_fresh(path, 10)
