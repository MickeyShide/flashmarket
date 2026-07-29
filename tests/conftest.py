"""Shared fixtures for end-to-end saga integration tests."""

from __future__ import annotations

import asyncio
import os
import subprocess
import time
import uuid
from collections.abc import AsyncIterator, Iterator
from contextlib import suppress
from urllib.parse import urljoin

import aio_pika
import httpx
import pytest
import pytest_asyncio
from aio_pika import ExchangeType

BASE_URL = os.getenv("FLASHMARKET_GATEWAY", "http://127.0.0.1:8080")
RABBITMQ_URL = os.getenv("FLASHMARKET_RABBITMQ", "amqp://guest:guest@127.0.0.1:5672/")


@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    """Provide a single event loop for the whole test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def gateway_ready() -> None:
    """Wait until the gateway is serving requests."""
    deadline = time.monotonic() + 120
    last_error = ""
    while time.monotonic() < deadline:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(urljoin(BASE_URL, "/health"))
                if resp.status_code == 200:
                    return
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
        await asyncio.sleep(1)
    pytest.fail(f"Gateway not ready: {last_error}")


@pytest_asyncio.fixture(scope="session")
async def rabbitmq_channel() -> AsyncIterator[aio_pika.abc.AbstractChannel]:
    """Provide a RabbitMQ channel connected to the shared broker."""
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        yield channel


@pytest_asyncio.fixture
async def api_client(
    gateway_ready: None,
) -> AsyncIterator[httpx.AsyncClient]:
    """Provide an async HTTP client pointed at the gateway."""
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=10.0,
        headers={"Accept": "application/json"},
    ) as client:
        yield client


@pytest_asyncio.fixture
async def unique_user() -> uuid.UUID:
    """Return a fresh UUID for a test user."""
    return uuid.uuid4()


def _service_url(service: str) -> str:
    """Return the direct URL for a service when bypassing the gateway."""
    port = {
        "auth": 8000,
        "catalog": 8010,
        "inventory": 8011,
        "orders": 8012,
        "payments": 8014,
        "notifications": 8016,
    }[service]
    return f"http://127.0.0.1:{port}"


@pytest.fixture
def service_url() -> callable:
    """Expose the service URL helper as a fixture."""
    return _service_url
