"""Tests for Catalog cache resource lifecycle."""

from unittest.mock import AsyncMock, Mock

from fastapi import FastAPI

import catalog.main as catalog_main


async def test_lifespan_closes_redis_client(monkeypatch) -> None:
    verifier = Mock()
    redis_client = AsyncMock()
    engine = AsyncMock()
    monkeypatch.setattr(catalog_main, "get_verifier", lambda: verifier)
    monkeypatch.setattr(catalog_main, "redis_client", redis_client)
    monkeypatch.setattr(catalog_main, "engine", engine)

    async with catalog_main.lifespan(FastAPI()):
        verifier.validate_startup.assert_called_once_with()

    redis_client.aclose.assert_awaited_once_with()
    engine.dispose.assert_awaited_once_with()
