"""Contracts for immutable production deployment of the Wishlist service."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_PATH = PROJECT_ROOT / ".github" / "workflows" / "wishlist-deploy.yml"
DEPLOY_COMPOSE_PATH = PROJECT_ROOT / "wishlist" / "docker-compose.deploy.yml"


def _workflow() -> str:
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def test_wishlist_image_exposes_digest_and_deploy_consumes_it() -> None:
    workflow = _workflow()

    assert "digest: ${{ steps.build.outputs.digest }}" in workflow
    assert "id: build" in workflow
    assert (
        "ghcr.io/mickeyshide/flashmarket-wishlist@${{ needs.image.outputs.digest }}"
        in workflow
    )
    assert "github.ref == 'refs/heads/main'" in workflow
    assert "startsWith(github.ref, 'refs/tags/wishlist-v')" in workflow
    assert "tests/test_wishlist_deployment_workflow.py" in workflow


def test_wishlist_deploy_renders_strict_production_configuration() -> None:
    workflow = _workflow()

    for setting in (
        "WISHLIST_ENVIRONMENT=production",
        "WISHLIST_DATABASE_URL=postgresql+asyncpg://%s:%s@shide-postgres:5432/wishlist",
        "WISHLIST_RABBITMQ_URL=amqp://%s:%s@shide-rabbitmq:5672/flashmarket",
        "WISHLIST_ALLOW_INSECURE_INTERNAL_SERVICES=true",
        "WISHLIST_DEBUG=false",
        "WISHLIST_DOCS_ENABLED=false",
        "WISHLIST_JWT_PUBLIC_KEY_DIR=/var/lib/flashmarket/keys/public",
        'WISHLIST_TRUSTED_HOSTS=["%s","wishlist.%s","localhost","127.0.0.1","wishlist","gateway"]',
    ):
        assert setting in workflow

    assert "DEPLOY_SSH_KEY is required" in workflow
    assert "POSTGRES_PASSWORD is required" in workflow
    assert "RABBITMQ_PASSWORD is required" in workflow
    assert "Wishlist image digest is missing" in workflow
    assert "ServerAliveInterval 15" in workflow
    assert "ServerAliveCountMax 4" in workflow
    assert "timeout --signal=TERM --kill-after=30s 900" in workflow


def test_wishlist_deploy_migrates_starts_runtime_and_verifies_gateway() -> None:
    workflow = _workflow()

    assert "timeout 120 docker compose" in workflow
    assert "run --rm --no-deps api migrate" in workflow
    assert "api consumer" in workflow
    assert "State.Running" in workflow
    assert "initial_consumer_restarts" in workflow
    assert "final_consumer_restarts" in workflow
    assert "Wishlist consumer restarted during deployment verification" in workflow
    assert "/dev/status/wishlist" in workflow
    assert "Wishlist is not reachable through the production gateway" in workflow


def test_wishlist_deploy_compose_owns_runtime_and_gateway_alias() -> None:
    compose = DEPLOY_COMPOSE_PATH.read_text(encoding="utf-8")

    assert "  api:" in compose
    assert "  consumer:" in compose
    assert "${WISHLIST_IMAGE:?WISHLIST_IMAGE must contain the image digest}" in compose
    assert "      aliases:\n        - wishlist" in compose
    assert "name: shide-observability" in compose
    assert "name: flashmarket-auth-jwt-keys-public" in compose
    assert "WISHLIST_LOG_FILE_PATH" not in compose
    assert "backend-logs" not in compose
    assert "http://localhost:8000/health/ready" in compose
    assert "ports:" not in compose
