"""Restart explicitly opted-in FlashMarket containers that stay unhealthy."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

LABEL = "flashmarket.autoheal=true"
STATE_PATH = Path("/var/lib/flashmarket/worker-watchdog.json")
COOLDOWN_SECONDS = 300


def _docker(*args: str) -> str:
    result = subprocess.run(
        ["docker", *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout.strip()


def _load_state(path: Path) -> dict[str, float]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return {str(key): float(value) for key, value in payload.items()}
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return {}


def _save_state(path: Path, state: dict[str, float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def run_once(*, state_path: Path = STATE_PATH, now: float | None = None) -> list[str]:
    current = time.time() if now is None else now
    state = _load_state(state_path)
    container_ids = _docker(
        "ps",
        "--quiet",
        "--filter",
        f"label={LABEL}",
        "--filter",
        "health=unhealthy",
    ).splitlines()
    restarted: list[str] = []
    for container_id in filter(None, container_ids):
        name = _docker("inspect", "--format", "{{.Name}}", container_id).lstrip("/")
        if current - state.get(name, 0.0) < COOLDOWN_SECONDS:
            continue
        _docker("restart", "--time", "20", container_id)
        state[name] = current
        restarted.append(name)
        print(f"Restarted unhealthy FlashMarket worker: {name}")
    state = {name: timestamp for name, timestamp in state.items() if current - timestamp < 86400}
    _save_state(state_path, state)
    return restarted


def main() -> None:
    try:
        run_once()
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"FlashMarket worker watchdog failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
