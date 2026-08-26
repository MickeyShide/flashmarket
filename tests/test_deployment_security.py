from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def _deployment_workflows() -> list[Path]:
    return sorted(
        path
        for path in WORKFLOWS.glob("*.yml")
        if "SSH_PRIVATE_KEY:" in path.read_text(encoding="utf-8")
    )


def test_deployments_verify_the_ssh_host_key() -> None:
    workflows = _deployment_workflows()
    assert workflows
    for workflow in workflows:
        contents = workflow.read_text(encoding="utf-8")
        assert "SSH_KNOWN_HOSTS: ${{ secrets.DEPLOY_KNOWN_HOSTS }}" in contents, workflow
        assert "bash scripts/configure-deploy-ssh.sh" in contents, workflow
        assert "StrictHostKeyChecking no" not in contents, workflow
        assert "UserKnownHostsFile /dev/null" not in contents, workflow


def test_deployments_do_not_contain_fallback_credentials() -> None:
    forbidden = (
        "flashmarket_postgres_pass_2026",
        "flashmarket_redis_pass_2026",
        "flashmarket_rabbitmq_pass_2026",
    )
    for workflow in WORKFLOWS.glob("*.yml"):
        contents = workflow.read_text(encoding="utf-8")
        for credential in forbidden:
            assert credential not in contents, workflow


def test_shared_ssh_configuration_is_strict_and_resilient() -> None:
    contents = (ROOT / "scripts" / "configure-deploy-ssh.sh").read_text(
        encoding="utf-8"
    )
    for setting in (
        "StrictHostKeyChecking yes",
        "UserKnownHostsFile ~/.ssh/known_hosts",
        "ConnectTimeout 15",
        "ServerAliveInterval 15",
        "ServerAliveCountMax 4",
    ):
        assert setting in contents


def test_production_deployments_are_serialized() -> None:
    workflows = [
        workflow
        for workflow in _deployment_workflows()
        if workflow.name != "reliability-ops-deploy.yml"
    ]
    assert workflows
    for workflow in workflows:
        contents = workflow.read_text(encoding="utf-8")
        assert "exec 9>/tmp/flashmarket-production-deploy.lock" in contents, workflow
        assert "flock -w 1800 9" in contents, workflow
        assert "timeout --signal=TERM --kill-after=30s 900" not in contents, workflow


def test_deployments_isolate_registry_credentials() -> None:
    workflows = [
        workflow
        for workflow in _deployment_workflows()
        if "Log server in to GHCR" in workflow.read_text(encoding="utf-8")
    ]
    assert workflows
    for workflow in workflows:
        contents = workflow.read_text(encoding="utf-8")
        assert 'docker_config="${DEPLOY_PATH}/.docker-' in contents, workflow
        assert "install -d -m 700 '$docker_config'" in contents, workflow
        assert "DOCKER_CONFIG='$docker_config' docker login" in contents, workflow
        assert 'export DOCKER_CONFIG="$DEPLOY_PATH/.docker-' in contents, workflow
        assert 'rm -f -- "$DOCKER_CONFIG/config.json"' in contents, workflow


def test_deployment_readiness_tolerates_transient_unhealthy_state() -> None:
    for workflow in _deployment_workflows():
        contents = workflow.read_text(encoding="utf-8")
        assert '"$health" == "unhealthy" || "$health" == "exited"' not in contents
        assert '"$worker_health" == "unhealthy"' not in contents
        assert '"$outbox_health" == "unhealthy"' not in contents
        assert '"$cleanup_health" == "unhealthy"' not in contents
