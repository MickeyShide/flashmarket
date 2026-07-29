"""FastAPI dependency injection wiring."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from payments.application.services.payment import PaymentService
from payments.infrastructure.database import get_db
from payments.infrastructure.repositories.payment import OutboxRepository, PaymentRepository

DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_payment_service(db: DbSession) -> PaymentService:
    """Build a payment service for the current request."""
    return PaymentService(
        session=db,
        payment_repo=PaymentRepository(db),
        outbox_repo=OutboxRepository(db),
    )


PaymentServiceDep = Annotated[PaymentService, Depends(get_payment_service)]
