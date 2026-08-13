"""Contracts for isolated Docker end-to-end orchestration."""

from pathlib import Path

from scripts.test_runner import E2ERunner


def test_e2e_override_names_every_fixed_name_container_uniquely(tmp_path: Path) -> None:
    runner = E2ERunner()
    runner.write_override(tmp_path)

    assert runner.override_path is not None
    override = runner.override_path.read_text(encoding="utf-8")
    assert "container_name: ${E2E_GATEWAY_CONTAINER}" in override
    assert "container_name: ${E2E_GATEWAY_EXPORTER_CONTAINER}" in override
    assert override.count("timeout: 15s") == 17
    assert runner.compose_env["E2E_GATEWAY_CONTAINER"].startswith(runner.project)
    assert runner.compose_env["E2E_GATEWAY_EXPORTER_CONTAINER"].startswith(runner.project)
    assert runner.minio.startswith(runner.project)
    assert len(runner.compose_env["S3_SECRET_KEY"]) >= 8
