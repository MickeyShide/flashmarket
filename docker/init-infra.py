#!/usr/bin/env python
"""Ensure shared infrastructure resources exist for FlashMarket services."""
from __future__ import annotations

import asyncio
import base64
import inspect
import json
import os
import re
import socket
import sys
import time
import urllib.parse
import urllib.request
from urllib.parse import urlparse

import asyncpg


def resolve_host_ipv4(host: str, port: int = 5432) -> str:
    """Force IPv4 (AF_INET) lookup with explicit port to bypass glibc servname and AAAA resolution failures."""
    try:
        infos = socket.getaddrinfo(host, port, family=socket.AF_INET, type=socket.SOCK_STREAM)
        if infos:
            return infos[0][4][0]
    except OSError as err:
        print(f"Warning: IPv4 resolution for {host}:{port} failed: {err}", file=sys.stderr)
    return host

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
                        await asyncio.sleep(RETRY_DELAY_SECONDS)
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
        "MEDIA_DATABASE_URL",
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
        "WISHLIST_RABBITMQ_URL",
    ]
    for key in keys:
        if val := os.environ.get(key):
            urls.append(val)
    return urls


def _get_celery_broker_urls() -> list[str]:
    """Return task-broker URLs whose vhosts need only permissions."""
    return [url] if (url := os.environ.get("CELERY_BROKER_URL")) else []


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


def _rabbitmq_vhost_from_url(raw_url: str) -> str:
    """Return the single AMQP vhost encoded by an AMQP connection URL."""
    path = urlparse(raw_url).path
    if path in {"", "/"}:
        return "/"
    return urllib.parse.unquote(path[1:])


def _ensure_vhost_and_permissions(
    raw_url: str,
    *,
    install_event_topology: bool = True,
) -> None:
    url = urlparse(raw_url)
    if not url.hostname:
        raise ValueError("RabbitMQ URL is missing a hostname")

    vhost = _rabbitmq_vhost_from_url(raw_url)

    user = urllib.parse.unquote(url.username or "guest")
    password = urllib.parse.unquote(url.password or "guest")
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

    encoded_vhost = urllib.parse.quote(vhost, safe="")

    vhost_url = f"{base}/vhosts/{encoded_vhost}"
    req = urllib.request.Request(vhost_url, headers=headers, method="PUT", data=b"{}")
    with urllib.request.urlopen(req, timeout=10.0) as resp:
        if resp.status not in (200, 201, 204):
            raise RuntimeError(
                f"RabbitMQ rejected vhost '{vhost}' creation with HTTP {resp.status}"
            )
    print(f"RabbitMQ vhost '{vhost}' created or verified")

    encoded_user = urllib.parse.quote(user, safe="")
    perm_url = f"{base}/permissions/{encoded_vhost}/{encoded_user}"
    perm_body = json.dumps({"configure": ".*", "write": ".*", "read": ".*"}).encode(
        "utf-8"
    )
    perm_req = urllib.request.Request(perm_url, headers=headers, method="PUT", data=perm_body)
    with urllib.request.urlopen(perm_req, timeout=10.0) as resp:
        if resp.status not in (200, 201, 204):
            raise RuntimeError(
                f"RabbitMQ rejected permissions for '{user}' on '{vhost}' "
                f"with HTTP {resp.status}"
            )
    print(f"Granted permissions for user '{user}' on vhost '{vhost}'")

    if not install_event_topology:
        return

    for exchange_name, exchange_type in (
        ("flashmarket.retry", "direct"),
        ("flashmarket.dead-letter", "direct"),
    ):
        encoded_exchange = urllib.parse.quote(exchange_name, safe="")
        exchange_url = f"{base}/exchanges/{encoded_vhost}/{encoded_exchange}"
        exchange_body = json.dumps(
            {
                "type": exchange_type,
                "durable": True,
                "auto_delete": False,
                "internal": False,
                "arguments": {},
            }
        ).encode("utf-8")
        exchange_req = urllib.request.Request(
            exchange_url, headers=headers, method="PUT", data=exchange_body
        )
        with urllib.request.urlopen(exchange_req, timeout=10.0) as resp:
            if resp.status not in (200, 201, 204):
                raise RuntimeError(
                    f"RabbitMQ rejected exchange '{exchange_name}' with HTTP {resp.status}"
                )
        print(f"Declared RabbitMQ exchange '{exchange_name}'")

    queue_policies = {
        "inventory.events": "inventory.events.dlq",
        "orders.events": "orders.events.dlq",
        "payments.events": "payments.events.dlq",
        "notifications.events": "notifications.events.dlq",
        "wishlist.drop-events": "wishlist.drop-events.dlq",
    }
    for queue_name, dlq_name in queue_policies.items():
        encoded_dlq = urllib.parse.quote(dlq_name, safe="")
        queue_url = f"{base}/queues/{encoded_vhost}/{encoded_dlq}"
        queue_body = json.dumps(
            {"durable": True, "auto_delete": False, "arguments": {}}
        ).encode("utf-8")
        queue_req = urllib.request.Request(
            queue_url, headers=headers, method="PUT", data=queue_body
        )
        with urllib.request.urlopen(queue_req, timeout=10.0) as resp:
            if resp.status not in (200, 201, 204):
                raise RuntimeError(
                    f"RabbitMQ rejected DLQ '{dlq_name}' with HTTP {resp.status}"
                )

        encoded_dlx = urllib.parse.quote("flashmarket.dead-letter", safe="")
        binding_url = f"{base}/bindings/{encoded_vhost}/e/{encoded_dlx}/q/{encoded_dlq}"
        binding_body = json.dumps(
            {"routing_key": dlq_name, "arguments": {}}
        ).encode("utf-8")
        binding_req = urllib.request.Request(
            binding_url, headers=headers, method="POST", data=binding_body
        )
        with urllib.request.urlopen(binding_req, timeout=10.0) as resp:
            if resp.status not in (200, 201, 204):
                raise RuntimeError(
                    f"RabbitMQ rejected DLQ binding '{dlq_name}' with HTTP {resp.status}"
                )

        policy_name = f"flashmarket-{queue_name}-limits"
        encoded_policy = urllib.parse.quote(policy_name, safe="")
        policy_url = f"{base}/policies/{encoded_vhost}/{encoded_policy}"
        policy_body = json.dumps(
            {
                "pattern": f"^{re.escape(queue_name)}$",
                "apply-to": "queues",
                "priority": 50,
                "definition": {
                    "max-length": 20_000,
                    "max-length-bytes": 128 * 1024 * 1024,
                    "overflow": "reject-publish-dlx",
                    "dead-letter-exchange": "flashmarket.dead-letter",
                    "dead-letter-routing-key": dlq_name,
                },
            }
        ).encode("utf-8")
        policy_req = urllib.request.Request(
            policy_url,
            headers=headers,
            method="PUT",
            data=policy_body,
        )
        with urllib.request.urlopen(policy_req, timeout=10.0) as resp:
            if resp.status not in (200, 201, 204):
                raise RuntimeError(
                    f"RabbitMQ rejected queue policy '{policy_name}' with HTTP {resp.status}"
                )
        print(f"Applied RabbitMQ queue policy '{policy_name}'")

        for suffix, max_length, max_bytes in (
            (r"\.retry\.[123]", 20_000, 128 * 1024 * 1024),
            (r"\.dlq", 50_000, 256 * 1024 * 1024),
        ):
            kind = "retry" if "retry" in suffix else "dlq"
            bounded_policy_name = f"flashmarket-{queue_name}-{kind}-limits"
            bounded_policy_url = (
                f"{base}/policies/{encoded_vhost}/"
                f"{urllib.parse.quote(bounded_policy_name, safe='')}"
            )
            bounded_body = json.dumps(
                {
                    "pattern": f"^{re.escape(queue_name)}{suffix}$",
                    "apply-to": "queues",
                    "priority": 50,
                    "definition": {
                        "max-length": max_length,
                        "max-length-bytes": max_bytes,
                        "overflow": "reject-publish",
                    },
                }
            ).encode("utf-8")
            bounded_request = urllib.request.Request(
                bounded_policy_url,
                headers=headers,
                method="PUT",
                data=bounded_body,
            )
            with urllib.request.urlopen(bounded_request, timeout=10.0) as resp:
                if resp.status not in (200, 201, 204):
                    raise RuntimeError(
                        f"RabbitMQ rejected queue policy '{bounded_policy_name}' "
                        f"with HTTP {resp.status}"
                    )
            print(f"Applied RabbitMQ queue policy '{bounded_policy_name}'")


@retry("Waiting for RabbitMQ management API")
def ensure_rabbitmq_vhost() -> None:
    urls = _get_rabbitmq_urls()
    celery_urls = _get_celery_broker_urls()
    if not urls and not celery_urls:
        print("No RabbitMQ URL configured in environment, skipping RabbitMQ initialization.")
        return

    initialized: set[str] = set()
    for raw_url in urls:
        _ensure_vhost_and_permissions(raw_url, install_event_topology=True)
        initialized.add(raw_url)
    for raw_url in celery_urls:
        if raw_url in initialized:
            continue
        _ensure_vhost_and_permissions(raw_url, install_event_topology=False)


async def main() -> None:
    await ensure_database()
    ensure_rabbitmq_vhost()


if __name__ == "__main__":
    asyncio.run(main())
