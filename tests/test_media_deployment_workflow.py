"""Contracts for immutable production deployment of the Media service."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_PATH = PROJECT_ROOT / ".github" / "workflows" / "media-ci.yml"
DEPLOY_COMPOSE_PATH = PROJECT_ROOT / "media" / "docker-compose.deploy.yml"


def _workflow() -> str:
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def test_media_image_exposes_digest_and_deploy_consumes_it() -> None:
    workflow = _workflow()

    assert "digest: ${{ steps.build.outputs.digest }}" in workflow
    assert "id: build" in workflow
    assert "ghcr.io/mickeyshide/flashmarket-media@${{ needs.image.outputs.digest }}" in workflow
    assert "github.ref == 'refs/heads/main'" in workflow
    assert "startsWith(github.ref, 'refs/tags/media-v')" in workflow


def test_media_deploy_renders_same_origin_storage_configuration() -> None:
    workflow = _workflow()

    for setting in (
        "MEDIA_ENVIRONMENT=production",
        "MEDIA_S3_INTERNAL_ENDPOINT=http://shide-minio:9000",
        "MEDIA_S3_PUBLIC_ENDPOINT=https://%s/media-storage",
        "MEDIA_PUBLIC_BASE_URL=https://%s/media-storage/%s",
        "MEDIA_ALLOW_INSECURE_INTERNAL_SERVICES=true",
        "MEDIA_DEBUG=false",
        "MEDIA_DOCS_ENABLED=false",
    ):
        assert setting in workflow

    assert "get_container_env shide-minio MINIO_ROOT_USER" in workflow
    assert "get_container_env shide-minio MINIO_ROOT_PASSWORD" in workflow
    assert "mc mb --ignore-existing" in workflow
    assert "mc anonymous set download" in workflow


def test_media_deploy_migrates_starts_all_runtime_and_verifies_gateway() -> None:
    workflow = _workflow()

    assert "run --rm --no-deps api migrate" in workflow
    assert "api cleanup" in workflow
    assert "/dev/status/media" in workflow
    assert "Media is not reachable through the production gateway" in workflow


def test_media_deploy_compose_owns_api_cleanup_and_network_alias() -> None:
    compose = DEPLOY_COMPOSE_PATH.read_text(encoding="utf-8")

    assert "  api:" in compose
    assert "  cleanup:" in compose
    assert "      aliases:\n        - media" in compose
    assert "name: shide-observability" in compose
