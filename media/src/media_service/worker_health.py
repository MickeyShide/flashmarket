"""Filesystem heartbeat used by the Media cleanup worker healthcheck."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

HEARTBEAT_PATH = Path("/tmp/flashmarket-heartbeat.json")


def touch(phase: str) -> None:
    temporary = HEARTBEAT_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps({"timestamp": time.time(), "phase": phase}), encoding="utf-8")
    os.replace(temporary, HEARTBEAT_PATH)


def main() -> None:
    max_age = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
    if not HEARTBEAT_PATH.is_file():
        raise SystemExit(1)
    try:
        payload = json.loads(HEARTBEAT_PATH.read_text(encoding="utf-8"))
        fresh = time.time() - float(payload["timestamp"]) <= max_age
    except KeyError, TypeError, ValueError, json.JSONDecodeError, OSError:
        fresh = False
    raise SystemExit(0 if fresh else 1)


if __name__ == "__main__":
    main()
