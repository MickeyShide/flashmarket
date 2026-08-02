"""Gateway routing and rate-limit configuration contract tests."""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
NGINX_CONF_PATH = PROJECT_ROOT / "gateway" / "nginx.conf"
GATEWAY_COMPOSE_PATH = PROJECT_ROOT / "gateway" / "docker-compose.yml"


def _config() -> str:
    """Return the gateway template as text."""
    return NGINX_CONF_PATH.read_text(encoding="utf-8")


def _extract_braced_block(content: str, declaration: str, *, start: int = 0) -> str:
    """Extract a simple Nginx block, including nested location blocks."""
    declaration_start = content.find(declaration, start)
    assert declaration_start >= 0, f"Missing declaration: {declaration}"
    opening_brace = content.find("{", declaration_start + len(declaration))
    assert opening_brace >= 0, f"Missing opening brace for: {declaration}"

    depth = 0
    for index in range(opening_brace, len(content)):
        if content[index] == "{":
            depth += 1
        elif content[index] == "}":
            depth -= 1
            if depth == 0:
                return content[declaration_start : index + 1]
    raise AssertionError(f"Unclosed block: {declaration}")


def _main_server(content: str) -> str:
    """Extract the default virtual server."""
    listen_position = content.find("listen 80 default_server;")
    assert listen_position >= 0
    server_position = content.rfind("server {", 0, listen_position)
    assert server_position >= 0
    return _extract_braced_block(content, "server", start=server_position)


def _service_server(content: str, service: str) -> str:
    """Extract one service-subdomain virtual server."""
    server_name = f"server_name {service}.${{GATEWAY_DOMAIN}};"
    name_position = content.find(server_name)
    assert name_position >= 0, f"Missing subdomain server for {service}"
    server_position = content.rfind("server {", 0, name_position)
    assert server_position >= 0
    return _extract_braced_block(content, "server", start=server_position)


def _storage_server(content: str) -> str:
    """Extract the isolated local object-storage listener."""
    listen_position = content.find("listen 9000;")
    assert listen_position >= 0
    server_position = content.rfind("server {", 0, listen_position)
    assert server_position >= 0
    return _extract_braced_block(content, "server", start=server_position)


def _location(server: str, declaration: str) -> str:
    """Extract a location from a previously isolated server block."""
    return _extract_braced_block(server, f"location {declaration} ")


def test_gw_001_nginx_conf_location_rules_exist() -> None:
    """GW-001: Verify all required service paths and admin routes are present in nginx.conf."""
    assert NGINX_CONF_PATH.exists(), f"gateway/nginx.conf file is missing at {NGINX_CONF_PATH}"

    content = _config()

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
        r"location /api/v1/media",
        r"location \^~ /api/v1/admin/drops",
    ]

    for loc in required_locations:
        assert re.search(loc, content), f"Missing location rule: {loc}"


def test_gw_002_admin_drops_priority_modifier() -> None:
    """GW-002: Verify admin drops route uses priority modifier ^~ to prevent falling through to /api/v1/admin."""
    content = _config()
    assert "location ^~ /api/v1/admin/drops" in content
    assert "set $upstream_drops http://drops:8000;" in content
    assert "proxy_pass $upstream_drops$request_uri;" in content


def test_gw_003_dynamic_upstream_targets() -> None:
    """GW-003: Verify every routed service has a request-time Docker DNS target."""
    content = _config()
    targets = {
        "auth": 8000,
        "catalog": 8000,
        "inventory": 8000,
        "orders": 8000,
        "payments": 8000,
        "notifications": 8000,
        "wishlist": 8000,
        "drops": 8000,
        "media": 8000,
        "frontend": 3000,
        "prometheus": 9090,
    }
    for service, port in targets.items():
        expected = f"set $upstream_{service} http://{service}:{port};"
        if service == "prometheus":
            expected = "set $upstream_prometheus http://shide-prometheus:9090;"
        assert expected in content, f"Missing dynamic upstream target: {expected}"


def test_gw_004_rate_limit_zones_and_global_policy() -> None:
    """GW-004: Four bounded zones expose the approved sustained rates."""
    content = _config()
    expected_zones = {
        "auth_limit": "5r/s",
        "transaction_limit": "10r/s",
        "catalog_limit": "50r/s",
        "general_limit": "20r/s",
    }

    for zone, rate in expected_zones.items():
        assert (
            f"limit_req_zone $rate_limit_client_key zone={zone}:10m rate={rate};"
            in content
        )

    assert "limit_req_status 429;" in content
    assert "limit_req_log_level warn;" in content
    assert "error_page 429 = @rate_limited;" in content


def test_gw_005_shared_real_ip_and_monitoring_exemptions() -> None:
    """GW-005: All servers share real-IP handling and monitoring uses an empty key."""
    content = _config()
    first_server = content.find("server {")
    assert first_server >= 0
    http_level = content[:first_server]

    for directive in (
        "set_real_ip_from 172.16.0.0/12;",
        "set_real_ip_from 127.0.0.1;",
        "real_ip_header X-Forwarded-For;",
        "real_ip_recursive on;",
    ):
        assert directive in http_level

    assert "default                       $binary_remote_addr;" in http_level
    assert '~^/health(?:/|$)              "";' in http_level
    assert '/metrics                      "";' in http_level
    assert '~^/prometheus(?:/|$)          "";' in http_level
    assert '/nginx_status                 "";' in http_level


def test_gw_006_main_domain_routes_use_expected_profiles() -> None:
    """GW-006: Every main-domain API and legacy Auth route selects one profile."""
    main = _main_server(_config())
    expected_locations = {
        "/api/v1/auth": "limit_req zone=auth_limit burst=10 nodelay;",
        "/api/v1/users": "limit_req zone=auth_limit burst=10 nodelay;",
        "/api/v1/sessions": "limit_req zone=auth_limit burst=10 nodelay;",
        "^~ /api/v1/admin/drops": "limit_req zone=catalog_limit burst=100 nodelay;",
        "/api/v1/admin": "limit_req zone=auth_limit burst=10 nodelay;",
        "/auth": "limit_req zone=auth_limit burst=10 nodelay;",
        "/sessions": "limit_req zone=auth_limit burst=10 nodelay;",
        "/users": "limit_req zone=auth_limit burst=10 nodelay;",
        "/admin": "limit_req zone=auth_limit burst=10 nodelay;",
        "/.well-known": "limit_req zone=auth_limit burst=10 nodelay;",
        "/api/v1/products": "limit_req zone=catalog_limit burst=100 nodelay;",
        "/api/v1/categories": "limit_req zone=catalog_limit burst=100 nodelay;",
        "/api/v1/brands": "limit_req zone=catalog_limit burst=100 nodelay;",
        "/api/v1/stocks": "limit_req zone=general_limit burst=40 nodelay;",
        "/api/v1/orders": "limit_req zone=transaction_limit burst=20 nodelay;",
        "/api/v1/promocodes": "limit_req zone=transaction_limit burst=20 nodelay;",
        "/api/v1/payments": "limit_req zone=transaction_limit burst=20 nodelay;",
        "/api/v1/notifications": "limit_req zone=general_limit burst=40 nodelay;",
        "/api/v1/wishlist": "limit_req zone=transaction_limit burst=20 nodelay;",
        "/api/v1/drops": "limit_req zone=catalog_limit burst=100 nodelay;",
        "/api/v1/media": "limit_req zone=transaction_limit burst=20 nodelay;",
    }

    for declaration, limiter in expected_locations.items():
        assert limiter in _location(main, declaration), declaration

    api_declarations = re.findall(
        r"^\s*location\s+((?:\^~\s+)?/api/[^\s{]+)\s*\{",
        main,
        flags=re.MULTILINE,
    )
    assert api_declarations
    for declaration in api_declarations:
        assert "limit_req zone=" in _location(main, declaration), declaration


def test_gw_007_service_subdomains_use_expected_profiles() -> None:
    """GW-007: Direct service domains share the same route-group quota."""
    content = _config()
    expected_services = {
        "auth": "limit_req zone=auth_limit burst=10 nodelay;",
        "catalog": "limit_req zone=catalog_limit burst=100 nodelay;",
        "inventory": "limit_req zone=general_limit burst=40 nodelay;",
        "orders": "limit_req zone=transaction_limit burst=20 nodelay;",
        "payments": "limit_req zone=transaction_limit burst=20 nodelay;",
        "notifications": "limit_req zone=general_limit burst=40 nodelay;",
        "wishlist": "limit_req zone=transaction_limit burst=20 nodelay;",
        "drops": "limit_req zone=catalog_limit burst=100 nodelay;",
        "media": "limit_req zone=transaction_limit burst=20 nodelay;",
    }

    for service, limiter in expected_services.items():
        server = _service_server(content, service)
        assert limiter in _location(server, "/"), service
        assert "location @rate_limited" in server


def test_gw_008_frontend_and_monitoring_locations_have_no_limiter() -> None:
    """GW-008: Static assets and service endpoints never consume API quota."""
    main = _main_server(_config())
    for declaration in ("/", "/health", "/prometheus", "/prometheus/", "= /nginx_status"):
        assert "limit_req zone=" not in _location(main, declaration), declaration


def test_gw_009_rate_limit_error_contract() -> None:
    """GW-009: Every public server can return the stable JSON 429 response."""
    content = _config()
    handler = """location @rate_limited {
        default_type application/json;
        add_header Retry-After "1" always;
        return 429 '{"error":{"code":"rate_limit_exceeded","message":"Too many requests"}}';
    }"""

    assert content.count(handler) == 10


def test_gw_010_developer_hub_readiness_routes_are_same_origin_and_read_only() -> None:
    """GW-010: Every documented service has a bounded same-origin readiness target."""
    content = _config()
    expected_services = (
        "auth",
        "catalog",
        "inventory",
        "orders",
        "payments",
        "notifications",
        "wishlist",
        "drops",
        "media",
    )

    for service in expected_services:
        assert (
            f"/dev/status/{service}" in content
            and f"http://{service}:8000/health/ready;" in content
        )

    main = _main_server(content)
    status_location = _location(main, "^~ /dev/status/")
    assert "limit_except GET" in status_location
    assert "proxy_connect_timeout 2s;" in status_location
    assert "proxy_read_timeout 3s;" in status_location
    assert "limit_req zone=" not in status_location


def test_gw_011_local_storage_listener_streams_to_shared_minio() -> None:
    """GW-011: Browser-visible uploads have a bounded listener outside the JSON API."""
    storage = _storage_server(_config())

    for directive in (
        "client_max_body_size 30m;",
        "set $upstream_storage http://shide-minio:9000;",
        "proxy_pass $upstream_storage$request_uri;",
        "proxy_set_header Host $http_host;",
        "proxy_hide_header Access-Control-Allow-Origin;",
        "add_header Access-Control-Allow-Origin $media_cors_origin always;",
        'add_header Access-Control-Allow-Methods "GET, HEAD, POST, OPTIONS" always;',
        "add_header Access-Control-Allow-Headers $http_access_control_request_headers always;",
        "proxy_request_buffering off;",
        "proxy_send_timeout 300s;",
        "proxy_read_timeout 300s;",
    ):
        assert directive in storage

    compose = GATEWAY_COMPOSE_PATH.read_text(encoding="utf-8")
    assert '"127.0.0.1:${MEDIA_STORAGE_PORT:-9000}:9000"' in compose

    content = _config()
    for origin in (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ):
        assert f"{origin}" in content
