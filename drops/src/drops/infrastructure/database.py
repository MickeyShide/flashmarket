"""Database engine, session factory, and ORM base class."""

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from drops.config import get_settings

settings = get_settings()


def _engine_options() -> dict[str, object]:
    options: dict[str, object] = {"pool_pre_ping": True}
    if settings.database_url.startswith("sqlite"):
        return options
    worker = os.getenv("FLASHMARKET_PROCESS_ROLE") == "worker"
    options.update(
        {
            "pool_size": settings.database_worker_pool_size
            if worker
            else settings.database_api_pool_size,
            "max_overflow": settings.database_worker_max_overflow
            if worker
            else settings.database_api_max_overflow,
            "pool_timeout": settings.database_pool_timeout_seconds,
            "pool_recycle": settings.database_pool_recycle_seconds,
        }
    )
    return options


engine = create_async_engine(
    settings.database_url,
    **_engine_options(),
)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def utc_now() -> datetime:
    """Return the current UTC-aware datetime."""
    return datetime.now(UTC)


async def get_db() -> AsyncIterator[AsyncSession]:
    """Yield a database session for one request."""
    async with SessionFactory() as session:
        try:
            yield session
        finally:
            await session.rollback()
