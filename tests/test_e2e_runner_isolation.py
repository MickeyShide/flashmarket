"""Contracts for isolated Docker end-to-end orchestration."""

from pathlib import Path

from scripts.test_runner import API_SERVICES, CRITICAL_SERVICES, E2ERunner

WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "saga-e2e.yml"


def test_e2e_override_names_every_fixed_name_container_uniquely(tmp_path: Path) -> None:
    runner = E2ERunner()
    runner.write_override(tmp_path)

    assert runner.override_path is not None
    override = runner.override_path.read_text(encoding="utf-8")
    assert "container_name: ${E2E_GATEWAY_CONTAINER}" in override
    assert "container_name: ${E2E_GATEWAY_EXPORTER_CONTAINER}" in override
    assert override.count("timeout: 15s") == 17
    assert runner.compose_env["E2E_GATEWAY_CONTAINER"].startswith(runner.project)
    assert runner.compose_env["E2E_GATEWAY_EXPORTER_CONTAINER"].startswith(
        runner.project
    )
    assert runner.minio.startswith(runner.project)
    assert len(runner.compose_env["S3_SECRET_KEY"]) >= 8


def test_ci_uses_the_isolated_e2e_runner() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "uv run python scripts/test_runner.py test-e2e" in workflow
    assert "docker compose up -d --build" not in workflow
    assert "docker rm -f shide-postgres" not in workflow


def test_e2e_starts_migrating_apis_before_workers(monkeypatch) -> None:
    runner = E2ERunner()
    compose_calls: list[tuple[str, ...]] = []
    health_checks: list[str] = []

    def fake_compose(*arguments: str, **_kwargs):
        compose_calls.append(arguments)

    def fake_service_health(service: str) -> str:
        health_checks.append(service)
        return "healthy"

    monkeypatch.setattr(runner, "compose", fake_compose)
    monkeypatch.setattr(runner, "service_health", fake_service_health)

    runner.start_stack()

    api_up = ("up", "-d", "--no-build", *API_SERVICES)
    full_up = ("up", "-d", "--no-build")
    assert compose_calls.index(api_up) < compose_calls.index(full_up)
    assert health_checks[: len(API_SERVICES)] == list(API_SERVICES)
    assert health_checks[len(API_SERVICES) :] == list(CRITICAL_SERVICES)
