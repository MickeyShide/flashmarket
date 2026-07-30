#!/usr/bin/env python
"""Ensure shared infrastructure resources exist for FlashMarket services."""
from __future__ import annotations

import asyncio
import os
import sys
import time
from urllib.parse import urlparse

import asyncpg
import httpx

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

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


@retry("Waiting for PostgreSQL")
async def ensure_database() -> None:
    url = urlparse(os.environ["DATABASE_URL"])
    target_db = url.path.lstrip("/")
    if not target_db:
        print("DATABASE_URL missing database name", file=sys.stderr)
        sys.exit(1)

    admin_dsn = url._replace(path="/postgres", scheme="postgresql").geturl()
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
    url = urlparse(os.environ["RABBITMQ_URL"])
    vhost = url.path.lstrip("/") or "/"
    user = url.username or "guest"
    password = url.password or "guest"
    host = url.hostname or "localhost"
    port = 15672

    auth = httpx.BasicAuth(user, password)
    base = f"http://{host}:{port}/api"

    with httpx.Client(timeout=10.0) as client:
        resp = client.get(f"{base}/vhosts/{vhost}", auth=auth)
        if resp.status_code == 200:
            print(f"RabbitMQ vhost '{vhost}' already exists")
            return
        if resp.status_code not in {404, 401}:
            resp.raise_for_status()
        encoded_vhost = vhost.replace("/", "%2F")
        resp = client.put(f"{base}/vhosts/{encoded_vhost}", auth=auth)
        resp.raise_for_status()
        print(f"RabbitMQ vhost '{vhost}' created")


async def main() -> None:
    await ensure_database()
    ensure_rabbitmq_vhost()


if __name__ == "__main__":
    asyncio.run(main())
