from sqlalchemy.ext.asyncio import AsyncSession

from auth_service.domain.events import DomainEvent
from auth_service.infrastructure.persistence.repositories import (
    SqlAlchemyAuditRepository,
    SqlAlchemySessionRepository,
    SqlAlchemyUserRepository,
)
from auth_service.models import OutboxEvent


class SqlAlchemyUnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.users = SqlAlchemyUserRepository(session)
        self.sessions = SqlAlchemySessionRepository(session)
        self.audit = SqlAlchemyAuditRepository(session)
        self._events: list[DomainEvent] = []

    def add_event(self, event: DomainEvent) -> None:
        self._events.append(event)

    async def commit(self) -> None:
        for event in self._events:
            self._session.add(
                OutboxEvent(
                    id=event.event_id,
                    event_type=event.event_type.value,
                    aggregate_type=event.aggregate_type,
                    aggregate_id=event.aggregate_id,
                    payload=event.message_payload(),
                    occurred_at=event.occurred_at,
                )
            )
        await self._session.commit()
        self._events.clear()

    async def rollback(self) -> None:
        self._events.clear()
        await self._session.rollback()
