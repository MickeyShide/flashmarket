"""Contracts for the host-level unhealthy worker watchdog."""

import importlib.util
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "flashmarket_worker_watchdog.py"


def _load():
    spec = importlib.util.spec_from_file_location("flashmarket_worker_watchdog", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_watchdog_restarts_only_returned_opted_in_unhealthy_workers(tmp_path: Path) -> None:
    module = _load()
    calls: list[tuple[str, ...]] = []

    def docker(*args: str) -> str:
        calls.append(args)
        if args[0] == "ps":
            assert "label=flashmarket.autoheal=true" in args
            assert "health=unhealthy" in args
            return "abc\n"
        if args[0] == "inspect":
            return "/flashmarket-orders-consumer"
        return ""

    with patch.object(module, "_docker", side_effect=docker):
        restarted = module.run_once(state_path=tmp_path / "state.json", now=1000)

    assert restarted == ["flashmarket-orders-consumer"]
    assert any(call[:2] == ("restart", "--time") for call in calls)


def test_watchdog_applies_restart_cooldown(tmp_path: Path) -> None:
    module = _load()
    state = tmp_path / "state.json"
    state.write_text('{"worker":900}', encoding="utf-8")

    def docker(*args: str) -> str:
        if args[0] == "ps":
            return "abc"
        if args[0] == "inspect":
            return "/worker"
        raise AssertionError("restart must be suppressed during cooldown")

    with patch.object(module, "_docker", side_effect=docker):
        assert module.run_once(state_path=state, now=1000) == []
