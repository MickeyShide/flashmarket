"""FastAPI dependency injection wiring."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from jwt_verifier import JWTVerifier, Principal, create_auth_dependencies
from sqlalchemy.ext.asyncio import AsyncSession

from payments.application.contracts import PaymentProvider
from payments.application.services.payment import PaymentService
from payments.config import get_settings
from payments.infrastructure.database import get_db
from payments.infrastructure.providers import get_shared_payment_provider
from payments.infrastructure.repositories.payment import (
    OutboxRepository,
    PaymentReceiptRepository,
    PaymentRepository,
)

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


def get_payment_provider() -> PaymentProvider:
    """Return the process-lifetime external payment provider."""
    return get_shared_payment_provider()


def get_payment_service(
    db: DbSession,
    provider: PaymentProvider = Depends(get_payment_provider),
) -> PaymentService:
    """Build a payment service for the current request."""
    settings = get_settings()
    return PaymentService(
        session=db,
        payment_repo=PaymentRepository(db),
        outbox_repo=OutboxRepository(db),
        receipt_repo=PaymentReceiptRepository(db),
        provider=provider,
        provider_name=settings.payment_provider,
        return_url=settings.yookassa_return_url or "http://localhost/payment/return",
        test_mode_required=settings.yookassa_test_mode_required,
        webhook_max_attempts=settings.webhook_max_attempts,
        attempt_ttl_seconds=settings.payment_attempt_ttl_seconds,
    )


PaymentServiceDep = Annotated[PaymentService, Depends(get_payment_service)]
