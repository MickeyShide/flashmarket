#!/usr/bin/env python
"""Ensure shared infrastructure resources exist for FlashMarket services."""
from __future__ import annotations

import asyncio
import base64
import inspect
import os
import socket
import sys
import time
import urllib.error
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
    ]:
        if val := os.environ.get(key):
            return val
    return None


def _get_rabbitmq_url() -> str | None:
    for key in [
        "RABBITMQ_URL",
        "INVENTORY_RABBITMQ_URL",
        "ORDERS_RABBITMQ_URL",
        "PAYMENTS_RABBITMQ_URL",
        "NOTIFICATIONS_RABBITMQ_URL",
    ]:
        if val := os.environ.get(key):
            return val
    return None


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


@retry("Waiting for RabbitMQ management API")
def ensure_rabbitmq_vhost() -> None:
    raw_url = _get_rabbitmq_url()
    if not raw_url:
        print("No RabbitMQ URL configured in environment, skipping RabbitMQ initialization.")
        return

    url = urlparse(raw_url)
    vhost = url.path.lstrip("/") or "/"
    user = url.username or "guest"
    password = url.password or "guest"
    host = url.hostname or "localhost"
    resolved_host = resolve_host_ipv4(host, 15672)
    port = 15672

    credentials = f"{user}:{password}"
    b64_auth = base64.b64encode(credentials.encode("ascii")).decode("ascii")
    headers = {"Authorization": f"Basic {b64_auth}"}

    base = f"http://{resolved_host}:{port}/api"
    check_url = f"{base}/vhosts/{vhost}"

    req = urllib.request.Request(check_url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            if resp.status == 200:
                print(f"RabbitMQ vhost '{vhost}' already exists")
                return
    except urllib.error.HTTPError as err:
        if err.code == 404:
            encoded_vhost = vhost.replace("/", "%2F")
            put_url = f"{base}/vhosts/{encoded_vhost}"
            put_req = urllib.request.Request(put_url, headers=headers, method="PUT")
            with urllib.request.urlopen(put_req, timeout=10.0) as put_resp:
                if put_resp.status in (200, 201):
                    print(f"RabbitMQ vhost '{vhost}' created")
                    return
        elif err.code == 401:
            raise err
        else:
            raise err


async def main() -> None:
    await ensure_database()
    ensure_rabbitmq_vhost()


if __name__ == "__main__":
    asyncio.run(main())
