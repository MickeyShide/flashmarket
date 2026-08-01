"""Async database engine and session factory."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from media_service.config import get_settings

settings = get_settings()
engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Declarative ORM base."""


def utc_now() -> datetime:
    """Return an aware UTC timestamp."""
    return datetime.now(UTC)


async def get_db() -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped transaction session."""
    async with SessionFactory() as session:
        try:
            yield session
        finally:
            await session.rollback()
