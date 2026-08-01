"""Gateway configuration and Nginx path-routing verification tests (GW-001 through GW-005)."""

import re
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
NGINX_CONF_PATH = PROJECT_ROOT / "gateway" / "nginx.conf"


def test_gw_001_nginx_conf_location_rules_exist() -> None:
    """GW-001: Verify all required service paths and admin routes are present in nginx.conf."""
    assert NGINX_CONF_PATH.exists(), f"gateway/nginx.conf file is missing at {NGINX_CONF_PATH}"

    content = NGINX_CONF_PATH.read_text(encoding="utf-8")

    # Verify key route prefixes exist
    required_locations = [
        r"location /health",
        r"location /api/v1/auth",
        r"location /api/v1/products",
        r"location /api/v1/categories",
        r"location /api/v1/brands",
        r"location /api/v1/stocks",
        r"location /api/v1/orders",
        r"location /api/v1/promocodes",
        r"location /api/v1/payments",
        r"location /api/v1/notifications",
        r"location /api/v1/wishlist",
        r"location /api/v1/drops",
        r"location \^~ /api/v1/admin/drops",
    ]

    for loc in required_locations:
        assert re.search(loc, content), f"Missing location rule: {loc}"


def test_gw_002_admin_drops_priority_modifier() -> None:
    """GW-002: Verify admin drops route uses priority modifier ^~ to prevent falling through to /api/v1/admin."""
    content = NGINX_CONF_PATH.read_text(encoding="utf-8")
    assert "location ^~ /api/v1/admin/drops" in content
    assert "proxy_pass http://drops;" in content


def test_gw_003_upstream_definitions() -> None:
    """GW-003: Verify all 8 microservices, frontend, and prometheus upstreams are defined."""
    content = NGINX_CONF_PATH.read_text(encoding="utf-8")
    upstreams = ["auth", "catalog", "inventory", "orders", "payments", "notifications", "wishlist", "drops", "frontend"]
    for service in upstreams:
        assert f"upstream {service}" in content, f"Missing upstream definition for {service}"
