"""FastAPI dependency injection wiring."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from jwt_verifier import JWTVerifier, Principal, create_auth_dependencies
from sqlalchemy.ext.asyncio import AsyncSession

from payments.application.services.payment import PaymentService
from payments.config import get_settings
from payments.infrastructure.database import get_db
from payments.infrastructure.repositories.payment import OutboxRepository, PaymentRepository

DbSession = Annotated[AsyncSession, Depends(get_db)]


@lru_cache
def get_verifier() -> JWTVerifier:
    settings = get_settings()
    return JWTVerifier(
        public_key_dir=settings.jwt_public_key_dir,
        algorithm=settings.jwt_algorithm,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )


get_optional_principal, get_current_principal, require_admin = create_auth_dependencies(
    get_verifier
)

OptionalPrincipal = Annotated[Principal | None, Depends(get_optional_principal)]
CurrentPrincipal = Annotated[Principal, Depends(get_current_principal)]
AdminPrincipal = Annotated[Principal, Depends(require_admin)]


def get_payment_service(db: DbSession) -> PaymentService:
    """Build a payment service for the current request."""
    return PaymentService(
        session=db,
        payment_repo=PaymentRepository(db),
        outbox_repo=OutboxRepository(db),
    )


PaymentServiceDep = Annotated[PaymentService, Depends(get_payment_service)]
