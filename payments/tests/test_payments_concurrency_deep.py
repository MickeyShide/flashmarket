"""Deep business rules, state transition, and idempotency tests for payments service."""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from payments.application.schemas import CreatePaymentRequest
from payments.application.services.payment import PaymentService
from payments.domain.entities import PaymentStatus
from payments.domain.exceptions import InvalidPaymentState
from payments.event_consumer import handle_payment_requested
from payments.infrastructure.models import OutboxEventModel, PaymentModel
from payments.infrastructure.repositories.payment import OutboxRepository, PaymentRepository


@pytest.mark.asyncio
async def test_terminal_state_isolation_prevents_conflicting_transitions(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """A payment transitioned to SUCCESS cannot subsequently be transitioned to FAILED."""
    order_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # Step 1: Create pending payment
    payment_id = None
    async with session_factory() as session:
        service = PaymentService(
            session=session,
            payment_repo=PaymentRepository(session),
            outbox_repo=OutboxRepository(session),
        )
        payment = await service.create_payment(
            CreatePaymentRequest(
                order_id=order_id,
                user_id=user_id,
                amount=5000,
                currency="RUB",
            )
        )
        payment_id = payment.id

    # Step 2: Confirm payment -> transitions to SUCCESS and emits PaymentSucceeded
    async with session_factory() as session:
        service = PaymentService(
            session=session,
            payment_repo=PaymentRepository(session),
            outbox_repo=OutboxRepository(session),
        )
        confirmed = await service.confirm_payment(payment_id)
        assert confirmed.status == PaymentStatus.SUCCESS

    # Step 3: Attempt to fail the already confirmed payment -> raises InvalidPaymentState
    async with session_factory() as session:
        service = PaymentService(
            session=session,
            payment_repo=PaymentRepository(session),
            outbox_repo=OutboxRepository(session),
        )
        with pytest.raises(InvalidPaymentState):
            await service.fail_payment(payment_id)

    # Step 4: Verify outbox contains exactly one terminal event (PaymentSucceeded)
    async with session_factory() as session:
        events = await session.scalars(
            select(OutboxEventModel).where(
                OutboxEventModel.event_type.in_(["PaymentSucceeded", "PaymentFailed"])
            )
        )
        all_events = events.all()
        assert len(all_events) == 1
        assert all_events[0].event_type == "PaymentSucceeded"


@pytest.mark.asyncio
async def test_duplicate_payment_requested_event_is_idempotent(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Duplicate delivery of PaymentRequested returns the existing payment idempotently."""
    order_id = uuid.uuid4()
    user_id = uuid.uuid4()
    payload = {
        "order_id": str(order_id),
        "user_id": str(user_id),
        "amount": 3500,
        "currency": "RUB",
    }

    # Delivery 1: Creates new payment record
    async with session_factory() as session, session.begin():
        await handle_payment_requested(session, payload)

    async with session_factory() as session:
        payment1 = await PaymentRepository(session).get_by_order_id(order_id)
        assert payment1 is not None
        assert payment1.order_id == order_id
        assert payment1.status == PaymentStatus.PENDING

    # Delivery 2: Re-delivery of identical payload returns existing payment without error
    async with session_factory() as session, session.begin():
        await handle_payment_requested(session, payload)

    # Verify only 1 payment row exists in DB
    async with session_factory() as session:
        payments = await session.scalars(
            select(PaymentModel).where(PaymentModel.order_id == order_id)
        )
        all_payments = payments.all()
        assert len(all_payments) == 1
        assert all_payments[0].id == payment1.id
