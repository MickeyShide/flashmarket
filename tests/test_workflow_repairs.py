"""Regression contracts for repository-wide workflow repairs."""

from __future__ import annotations

from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
SETUP_UV_REVISION = "c771a70e6277c0a99b617c7a806ffedaca235ff9"


def test_node_actions_use_supported_or_pinned_revisions() -> None:
    for workflow in WORKFLOWS.glob("*.yml"):
        contents = workflow.read_text(encoding="utf-8")
        for line in contents.splitlines():
            if "uses: actions/checkout@" in line:
                assert "uses: actions/checkout@v7" in line, workflow
            if "uses: astral-sh/setup-uv@" in line:
                assert f"uses: astral-sh/setup-uv@{SETUP_UV_REVISION}" in line, workflow


def test_image_deployments_emit_container_diagnostics() -> None:
    deployments = [
        workflow
        for workflow in WORKFLOWS.glob("*.yml")
        if "Log server in to GHCR" in workflow.read_text(encoding="utf-8")
    ]
    assert deployments
    for workflow in deployments:
        contents = workflow.read_text(encoding="utf-8")
        assert "diagnose_service()" in contents, workflow
        assert "Missing deployment container" in contents, workflow
        assert "status={{.State.Status}},exit={{.State.ExitCode}}" in contents, workflow
        assert ".State.Health.Log" in contents, workflow


def test_orders_declares_runtime_httpx_and_import_guard() -> None:
    pyproject = tomllib.loads(
        (ROOT / "orders" / "pyproject.toml").read_text(encoding="utf-8")
    )
    runtime = pyproject["project"]["dependencies"]
    development = pyproject["dependency-groups"]["dev"]
    workflow = (WORKFLOWS / "orders-deploy.yml").read_text(encoding="utf-8")

    assert any(dependency.startswith("httpx") for dependency in runtime)
    assert not any(dependency.startswith("httpx") for dependency in development)
    assert "Verify runtime-only application import" in workflow
    assert 'uv run --no-dev python -c "import orders.main"' in workflow


def test_purchase_saga_uses_admin_for_payment_state_transitions() -> None:
    saga_test = (ROOT / "tests" / "test_purchase_saga.py").read_text(encoding="utf-8")

    assert "confirm_resp = await admin_api_client.post(" in saga_test
    assert "fail_resp = await admin_api_client.post(" in saga_test
