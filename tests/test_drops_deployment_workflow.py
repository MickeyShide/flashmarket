"""Contracts for immutable production deployment of the Drops service."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_PATH = PROJECT_ROOT / ".github" / "workflows" / "drops-deploy.yml"
DEPLOY_COMPOSE_PATH = PROJECT_ROOT / "drops" / "docker-compose.deploy.yml"


def _workflow() -> str:
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def test_drops_image_exposes_digest_and_deploy_consumes_it() -> None:
    workflow = _workflow()

    assert "digest: ${{ steps.build.outputs.digest }}" in workflow
    assert "id: build" in workflow
    assert (
        "ghcr.io/mickeyshide/flashmarket-drops@${{ needs.image.outputs.digest }}"
        in workflow
    )
    assert "github.ref == 'refs/heads/main'" in workflow
    assert "startsWith(github.ref, 'refs/tags/drops-v')" in workflow


def test_drops_deploy_renders_strict_production_configuration() -> None:
    workflow = _workflow()

    for setting in (
        "DROPS_ENVIRONMENT=production",
        "DROPS_DATABASE_URL=postgresql+asyncpg://%s:%s@shide-postgres:5432/drops",
        "DROPS_RABBITMQ_URL=amqp://%s:%s@shide-rabbitmq:5672/flashmarket",
        "DROPS_ALLOW_INSECURE_INTERNAL_SERVICES=true",
        "DROPS_DEBUG=false",
        "DROPS_DOCS_ENABLED=false",
        "DROPS_JWT_PUBLIC_KEY_DIR=/var/lib/flashmarket/keys/public",
    ):
        assert setting in workflow

    assert "DEPLOY_SSH_KEY is required" in workflow
    assert "Drops image digest is missing" in workflow
    assert "bash scripts/configure-deploy-ssh.sh" in workflow
    assert "timeout --signal=TERM --kill-after=30s 900" in workflow


def test_drops_deploy_migrates_starts_all_runtime_and_verifies_gateway() -> None:
    workflow = _workflow()

    assert "run --rm --no-deps api migrate" in workflow
    assert "api scheduler outbox" in workflow
    assert "/dev/status/drops" in workflow
    assert "Drops is not reachable through the production gateway" in workflow


def test_drops_deploy_compose_owns_runtime_and_gateway_alias() -> None:
    compose = DEPLOY_COMPOSE_PATH.read_text(encoding="utf-8")

    assert "  api:" in compose
    assert "  scheduler:" in compose
    assert "  outbox:" in compose
    assert "        aliases:\n          - drops" in compose
    assert "name: shide-observability" in compose
    assert "name: flashmarket-auth-jwt-keys-public" in compose
