"""Developer Hub OpenAPI generator contract tests."""

from __future__ import annotations

import json
from pathlib import Path

from tools.openapi.generate import (
    ServiceDefinition,
    discover_gateway_routes,
    discover_services,
    merge_documents,
    namespace_document,
)

ROOT = Path(__file__).resolve().parents[1]


def test_dev_001_discovers_every_main_gateway_api_service() -> None:
    routes = discover_gateway_routes((ROOT / "gateway" / "nginx.conf").read_text(encoding="utf-8"))
    services = discover_services(ROOT, routes)
    assert [service.id for service in services] == [
        "auth",
        "catalog",
        "drops",
        "inventory",
        "media",
        "notifications",
        "orders",
        "payments",
        "wishlist",
    ]
    assert "/api/v1/products" in routes["catalog"]
    assert "/internal" not in {prefix for values in routes.values() for prefix in values}


def test_dev_002_namespaces_schemas_and_normalizes_bearer_security() -> None:
    source = {
        "components": {
            "schemas": {"Item": {"type": "object"}},
            "securitySchemes": {"HTTPBearer": {"type": "http", "scheme": "bearer"}},
        },
        "paths": {
            "/api/v1/items": {
                "get": {
                    "security": [{"HTTPBearer": []}],
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Item"}
                                }
                            }
                        }
                    },
                }
            }
        },
    }
    result = namespace_document(source, "catalog")
    operation = result["paths"]["/api/v1/items"]["get"]
    assert "CatalogItem" in result["components"]["schemas"]
    assert operation["security"] == [{"bearerAuth": []}]
    assert (
        operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/CatalogItem"
    )


def test_dev_003_merge_keeps_only_gateway_prefix_and_real_access_metadata(tmp_path: Path) -> None:
    service = ServiceDefinition("catalog", tmp_path, "catalog.main", ("/api/v1/products",))
    document = {
        "openapi": "3.1.0",
        "info": {"title": "FlashMarket Catalog", "version": "0.1.0"},
        "paths": {
            "/api/v1/products": {
                "get": {
                    "operationId": "list_products",
                    "x-flashmarket-access": "anonymous",
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/health/ready": {
                "get": {
                    "operationId": "health",
                    "x-flashmarket-access": "anonymous",
                    "responses": {"200": {"description": "OK"}},
                }
            },
        },
        "components": {},
    }
    merged, metadata = merge_documents([service], {"catalog": document})
    assert list(merged["paths"]) == ["/api/v1/products"]
    assert merged["paths"]["/api/v1/products"]["get"]["security"] == []
    assert metadata["operationCount"] == 1
    assert metadata["services"][0]["statusUrl"] == "/dev/status/catalog"


def test_dev_004_generated_production_contract_contains_no_operational_routes() -> None:
    contract_path = ROOT / "frontend" / "public" / "dev" / "openapi.json"
    metadata_path = ROOT / "frontend" / "public" / "dev" / "services.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert contract["servers"] == [{"description": "Current FlashMarket domain", "url": "/"}]
    assert metadata["serviceCount"] == 9
    assert metadata["operationCount"] > 0
    assert all(
        not path.startswith(("/internal", "/health", "/metrics", "/docs", "/redoc"))
        for path in contract["paths"]
    )
    for path_item in contract["paths"].values():
        for method, operation in path_item.items():
            if method in {"get", "post", "put", "patch", "delete", "options", "head", "trace"}:
                assert operation["x-flashmarket-access"] in {
                    "anonymous",
                    "authenticated",
                    "admin",
                }
                assert operation["x-flashmarket-service"]
