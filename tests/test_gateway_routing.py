"""Gateway configuration and Nginx path-routing verification tests (GW-001 through GW-005)."""

import re
from pathlib import Path

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
    assert "set $upstream_drops http://drops:8000;" in content
    assert "proxy_pass $upstream_drops$request_uri;" in content


def test_gw_003_dynamic_upstream_targets() -> None:
    """GW-003: Verify every routed service has a request-time Docker DNS target."""
    content = NGINX_CONF_PATH.read_text(encoding="utf-8")
    targets = {
        "auth": 8000,
        "catalog": 8000,
        "inventory": 8000,
        "orders": 8000,
        "payments": 8000,
        "notifications": 8000,
        "wishlist": 8000,
        "drops": 8000,
        "frontend": 3000,
        "prometheus": 9090,
    }
    for service, port in targets.items():
        expected = f"set $upstream_{service} http://{service}:{port};"
        if service == "prometheus":
            expected = "set $upstream_prometheus http://shide-prometheus:9090;"
        assert expected in content, f"Missing dynamic upstream target: {expected}"
