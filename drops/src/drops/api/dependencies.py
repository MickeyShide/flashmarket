"""FastAPI dependencies for dependency injection."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from drops.application.services.drop import DropService
from drops.infrastructure.database import get_db
from drops.infrastructure.repositories.drop import DropRepository
from drops.infrastructure.repositories.outbox import OutboxRepository

DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_drop_service(db: DbSession) -> DropService:
    """Instantiate and provide DropService with repositories."""
    repo = DropRepository(db)
    outbox_repo = OutboxRepository(db)
    return DropService(session=db, repo=repo, outbox_repo=outbox_repo)


DropServiceDep = Annotated[DropService, Depends(get_drop_service)]
