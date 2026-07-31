#!/usr/bin/env python
"""Ensure shared infrastructure resources exist for FlashMarket services."""
from __future__ import annotations

import asyncio
import base64
import inspect
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from urllib.parse import urlparse


def resolve_host_ipv4(host: str, port: int = 5432) -> str:
    """Force IPv4 (AF_INET) lookup with explicit port to bypass glibc servname and AAAA resolution failures."""
    try:
        infos = socket.getaddrinfo(host, port, family=socket.AF_INET, type=socket.SOCK_STREAM)
        if infos:
            return infos[0][4][0]
    except Exception as err:
        print(f"Warning: IPv4 resolution for {host}:{port} failed: {err}", file=sys.stderr)
    return host

import asyncpg

MAX_RETRIES = 30
RETRY_DELAY_SECONDS = 2


def retry(message: str):
    def decorator(func):
        async def async_wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
            last_exc: Exception | None = None
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                    print(f"{message} (attempt {attempt}/{MAX_RETRIES}): {exc}")
                    if attempt < MAX_RETRIES:
                        time.sleep(RETRY_DELAY_SECONDS)
            raise last_exc  # type: ignore[misc]

        def sync_wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
            last_exc: Exception | None = None
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                    print(f"{message} (attempt {attempt}/{MAX_RETRIES}): {exc}")
                    if attempt < MAX_RETRIES:
                        time.sleep(RETRY_DELAY_SECONDS)
            raise last_exc  # type: ignore[misc]

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def _get_db_url() -> str | None:
    for key in [
        "DATABASE_URL",
        "CATALOG_DATABASE_URL",
        "AUTH_DATABASE_URL",
        "INVENTORY_DATABASE_URL",
        "ORDERS_DATABASE_URL",
        "PAYMENTS_DATABASE_URL",
        "NOTIFICATIONS_DATABASE_URL",
        "WISHLIST_DATABASE_URL",
        "DROPS_DATABASE_URL",
    ]:
        if val := os.environ.get(key):
            return val
    return None


def _get_rabbitmq_urls() -> list[str]:
    urls = []
    keys = [
        "RABBITMQ_URL",
        "AUTH_RABBITMQ_URL",
        "CATALOG_RABBITMQ_URL",
        "INVENTORY_RABBITMQ_URL",
        "ORDERS_RABBITMQ_URL",
        "PAYMENTS_RABBITMQ_URL",
        "NOTIFICATIONS_RABBITMQ_URL",
        "DROPS_RABBITMQ_URL",
    ]
    for key in keys:
        if val := os.environ.get(key):
            urls.append(val)
    return urls


@retry("Waiting for PostgreSQL")
async def ensure_database() -> None:
    raw_url = _get_db_url()
    if not raw_url:
        print("No database URL configured in environment, skipping DB initialization.")
        return

    url = urlparse(raw_url)
    target_db = url.path.lstrip("/")
    if not target_db:
        print("Database URL missing database name", file=sys.stderr)
        sys.exit(1)

    admin_dsn = url._replace(path="/postgres", scheme="postgresql").geturl()
    if url.hostname:
        db_port = url.port or 5432
        resolved_ip = resolve_host_ipv4(url.hostname, db_port)
        admin_dsn = admin_dsn.replace(f"@{url.hostname}:", f"@{resolved_ip}:")
    conn = await asyncpg.connect(admin_dsn)
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", target_db
        )
        if exists:
            print(f"PostgreSQL database '{target_db}' already exists")
            return
        await conn.execute(f'CREATE DATABASE "{target_db}"')
        print(f"PostgreSQL database '{target_db}' created")
    finally:
        await conn.close()


def _ensure_vhost_and_permissions(raw_url: str) -> None:
    url = urlparse(raw_url)
    if not url.hostname:
        return

    path = url.path
    if path.startswith("//"):
        vhosts_to_create = [path[1:], path.lstrip("/")]
    elif path.startswith("/"):
        vhost_stripped = path.lstrip("/")
        if vhost_stripped:
            vhosts_to_create = [f"/{vhost_stripped}", vhost_stripped]
        else:
            vhosts_to_create = ["/"]
    else:
        vhosts_to_create = ["/"]

    user = url.username or "guest"
    password = url.password or "guest"
    host = url.hostname or "localhost"
    resolved_host = resolve_host_ipv4(host, 15672)
    port = 15672

    credentials = f"{user}:{password}"
    b64_auth = base64.b64encode(credentials.encode("ascii")).decode("ascii")
    headers = {
        "Authorization": f"Basic {b64_auth}",
        "Content-Type": "application/json"
    }
    base = f"http://{resolved_host}:{port}/api"

    for vhost in vhosts_to_create:
        encoded_vhost = urllib.parse.quote(vhost, safe="")

        # 1. Create vhost
        vhost_url = f"{base}/vhosts/{encoded_vhost}"
        req = urllib.request.Request(vhost_url, headers=headers, method="PUT", data=b"{}")
        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                if resp.status in (200, 201, 204):
                    print(f"RabbitMQ vhost '{vhost}' created or verified")
        except urllib.error.HTTPError as err:
            if err.code != 204:
                print(f"Warning: PUT vhost '{vhost}' code {err.code}: {err.reason}", file=sys.stderr)
        except Exception as exc:
            print(f"Warning: Failed to create vhost '{vhost}': {exc}", file=sys.stderr)

        # 2. Set user permissions
        perm_url = f"{base}/permissions/{encoded_vhost}/{user}"
        perm_body = json.dumps({"configure": ".*", "write": ".*", "read": ".*"}).encode("utf-8")
        perm_req = urllib.request.Request(perm_url, headers=headers, method="PUT", data=perm_body)
        try:
            with urllib.request.urlopen(perm_req, timeout=10.0) as resp:
                if resp.status in (200, 201, 204):
                    print(f"Granted permissions for user '{user}' on vhost '{vhost}'")
        except Exception as exc:
            print(f"Warning: Failed to set permissions for user '{user}' on vhost '{vhost}': {exc}", file=sys.stderr)


@retry("Waiting for RabbitMQ management API")
def ensure_rabbitmq_vhost() -> None:
    urls = _get_rabbitmq_urls()
    if not urls:
        print("No RabbitMQ URL configured in environment, skipping RabbitMQ initialization.")
        return

    for raw_url in urls:
        _ensure_vhost_and_permissions(raw_url)


async def main() -> None:
    await ensure_database()
    ensure_rabbitmq_vhost()


if __name__ == "__main__":
    asyncio.run(main())
