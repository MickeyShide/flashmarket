"""Shared fixtures for end-to-end saga integration tests."""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from collections.abc import AsyncIterator, Iterator
from urllib.parse import urljoin

import aio_pika
import httpx
import pytest
import pytest_asyncio
from aio_pika import ExchangeType

BASE_URL = os.getenv("FLASHMARKET_GATEWAY", "http://127.0.0.1:8080")
RABBITMQ_URL = os.getenv("FLASHMARKET_RABBITMQ", "amqp://guest:guest@127.0.0.1:5672/")
SAGA_ADMIN_EMAIL = os.getenv("SAGA_ADMIN_EMAIL", "saga-admin@example.com")
SAGA_ADMIN_PASSWORD = os.getenv("SAGA_ADMIN_PASSWORD", "SagaAdminPassword123!")


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
    customer_access_token: str,
) -> AsyncIterator[httpx.AsyncClient]:
    """Provide a customer-authenticated client pointed at the gateway."""
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=10.0,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {customer_access_token}",
        },
    ) as client:
        yield client


@pytest_asyncio.fixture
async def authenticated_user(gateway_ready: None) -> tuple[uuid.UUID, str]:
    """Register a distinct customer and return its ID and access token."""
    email = f"saga-{uuid.uuid4().hex}@example.com"
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        response = await client.post(
            "/auth/register",
            json={
                "email": email,
                "password": "SagaCustomerPassword123!",
                "full_name": "Saga E2E Customer",
            },
        )
    assert response.status_code == 201, response.text
    payload = response.json()
    return uuid.UUID(payload["user"]["id"]), payload["tokens"]["access_token"]


@pytest.fixture
def unique_user(authenticated_user: tuple[uuid.UUID, str]) -> uuid.UUID:
    """Return the ID encoded into the test customer's access token."""
    return authenticated_user[0]


@pytest.fixture
def customer_access_token(authenticated_user: tuple[uuid.UUID, str]) -> str:
    """Return the test customer's Auth-issued access token."""
    return authenticated_user[1]


@pytest_asyncio.fixture(scope="session")
async def admin_access_token(gateway_ready: None) -> str:
    """Log in the administrator bootstrapped by the E2E workflow."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        response = await client.post(
            "/auth/login",
            json={"email": SAGA_ADMIN_EMAIL, "password": SAGA_ADMIN_PASSWORD},
        )
    assert response.status_code == 200, response.text
    return response.json()["tokens"]["access_token"]


@pytest_asyncio.fixture
async def admin_api_client(
    admin_access_token: str,
) -> AsyncIterator[httpx.AsyncClient]:
    """Provide an administrator-authenticated Gateway client."""
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=10.0,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {admin_access_token}",
        },
    ) as client:
        yield client


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
