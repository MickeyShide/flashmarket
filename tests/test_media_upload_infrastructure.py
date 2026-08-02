"""Contracts for browser-visible object-storage upload infrastructure."""

from pathlib import Path
from xml.etree import ElementTree

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRODUCTION_CORS_PATH = PROJECT_ROOT / "media" / "cors" / "production.example.xml"
MEDIA_COMPOSE_PATH = PROJECT_ROOT / "media" / "docker-compose.yml"


def _cors_values(name: str) -> set[str]:
    root = ElementTree.parse(PRODUCTION_CORS_PATH).getroot()
    namespace = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
    return {element.text or "" for element in root.findall(f".//s3:{name}", namespace)}


def test_production_bucket_cors_example_covers_direct_upload_contract() -> None:
    assert _cors_values("AllowedOrigin") == {
        "https://shop.example.com",
        "https://admin.example.com",
    }
    assert _cors_values("AllowedMethod") == {"GET", "HEAD", "POST"}
    assert _cors_values("AllowedHeader") == {"*"}
    assert {"ETag", "x-amz-request-id"} <= _cors_values("ExposeHeader")


def test_media_api_cors_defaults_cover_gateway_and_vite_hostnames() -> None:
    compose = MEDIA_COMPOSE_PATH.read_text(encoding="utf-8")

    for origin in (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ):
        assert origin in compose
