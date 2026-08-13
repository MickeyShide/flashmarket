"""Atomic file heartbeat and Docker healthcheck command."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from .metrics import mark_worker_success, start_worker_metrics_server


def touch_heartbeat(path: str | Path, phase: str) -> None:
    ensure_worker_metrics_server()
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps({"timestamp": time.time(), "phase": phase}, separators=(",", ":")),
        encoding="utf-8",
    )
    temporary.replace(target)
    mark_worker_success(phase)


def ensure_worker_metrics_server() -> None:
    start_worker_metrics_server(int(os.getenv("FLASHMARKET_WORKER_METRICS_PORT", "9100")))


def heartbeat_is_fresh(path: str | Path, max_age_seconds: float) -> bool:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        age = time.time() - float(payload["timestamp"])
    except OSError, KeyError, TypeError, ValueError, json.JSONDecodeError:
        return False
    return -5 <= age <= max_age_seconds


@asynccontextmanager
async def periodic_heartbeat(
    path: str | Path,
    *,
    interval_seconds: float = 10.0,
    phase: str = "connected",
) -> AsyncIterator[None]:
    """Keep an idle but connected worker healthy until its scope exits."""
    ensure_worker_metrics_server()

    async def beat() -> None:
        while True:
            touch_heartbeat(path, phase)
            await asyncio.sleep(interval_seconds)

    task = asyncio.create_task(beat())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("max_age_seconds", type=float)
    args = parser.parse_args()
    raise SystemExit(0 if heartbeat_is_fresh(args.path, args.max_age_seconds) else 1)


if __name__ == "__main__":
    main()
