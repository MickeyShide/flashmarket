"""SQLAlchemy ORM models for the payments database."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from payments.domain.entities import (
    PaymentAttemptStatus,
    PaymentStatus,
    ProviderOperationStatus,
    RefundStatus,
    WebhookInboxStatus,
)
from payments.infrastructure.database import Base, utc_now


class PaymentModel(Base):
    """Payment attempt bound to an order."""

    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
        UniqueConstraint("order_id", name="uq_payments_order_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid7)
    order_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="RUB")
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        String(20),
        nullable=False,
        default=PaymentStatus.PENDING,
        server_default="PENDING",
    )
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confirmation_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_test: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    refund_external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    refund_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    current_attempt_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


class ProviderOperationModel(Base):
    """Durable identity and outcome of a financial provider POST."""

    __tablename__ = "provider_operations"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_provider_operations_idempotency_key"),
        UniqueConstraint(
            "operation_type",
            "entity_id",
            name="uq_provider_operations_type_entity",
        ),
        Index(
            "ix_provider_operations_recovery",
            "status",
            "next_attempt_at",
            "created_at",
        ),
        CheckConstraint("attempt_count >= 0", name="ck_provider_operations_attempts"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid7)
    operation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    payment_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    request_payload: Mapped[str] = mapped_column(Text, nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[ProviderOperationStatus] = mapped_column(
        String(20),
        nullable=False,
        default=ProviderOperationStatus.NEW,
        server_default="NEW",
    )
    external_id: Mapped[str | None] = mapped_column(String(255), index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    first_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    claim_token: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    claimed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_code: Mapped[str | None] = mapped_column(String(64))
    response_payload: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class PaymentAttemptModel(Base):
    """One provider checkout attempt for an order-level payment aggregate."""

    __tablename__ = "payment_attempts"
    __table_args__ = (
        UniqueConstraint("payment_id", "attempt_number", name="uq_payment_attempts_number"),
        Index(
            "uq_payment_attempts_active",
            "payment_id",
            unique=True,
            postgresql_where=text("status IN ('NEW','PREPARING','UNKNOWN','PENDING')"),
            sqlite_where=text("status IN ('NEW','PREPARING','UNKNOWN','PENDING')"),
        ),
        CheckConstraint("amount > 0", name="ck_payment_attempts_amount_positive"),
        CheckConstraint("attempt_number > 0", name="ck_payment_attempts_number_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid7)
    payment_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[PaymentAttemptStatus] = mapped_column(
        String(20),
        nullable=False,
        default=PaymentAttemptStatus.NEW,
        server_default="NEW",
    )
    external_id: Mapped[str | None] = mapped_column(String(255), index=True)
    external_status: Mapped[str | None] = mapped_column(String(64))
    confirmation_url: Mapped[str | None] = mapped_column(String(2048))
    cancellation_party: Mapped[str | None] = mapped_column(String(64))
    cancellation_reason: Mapped[str | None] = mapped_column(String(255))
    provider_test: Mapped[bool | None] = mapped_column(Boolean)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class RefundModel(Base):
    """One full or partial refund against a captured payment."""

    __tablename__ = "refunds"
    __table_args__ = (
        UniqueConstraint("request_key", name="uq_refunds_request_key"),
        CheckConstraint("amount > 0", name="ck_refunds_amount_positive"),
        Index("ix_refunds_reconcile", "status", "next_attempt_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid7)
    payment_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    parent_refund_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    request_key: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[RefundStatus] = mapped_column(
        String(20), nullable=False, default=RefundStatus.NEW, server_default="NEW"
    )
    external_id: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    external_status: Mapped[str | None] = mapped_column(String(64))
    cancellation_party: Mapped[str | None] = mapped_column(String(64))
    cancellation_reason: Mapped[str | None] = mapped_column(String(255))
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    claim_token: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    claimed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class WebhookInboxModel(Base):
    """Durably accepted provider notification awaiting verified processing."""

    __tablename__ = "webhook_inbox"
    __table_args__ = (
        UniqueConstraint("dedupe_hash", name="uq_webhook_inbox_dedupe_hash"),
        Index("ix_webhook_inbox_due", "status", "next_attempt_at", "received_at"),
        CheckConstraint("attempt_count >= 0", name="ck_webhook_inbox_attempts"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid7)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    object_type: Mapped[str | None] = mapped_column(String(32))
    external_id: Mapped[str | None] = mapped_column(String(255), index=True)
    event: Mapped[str | None] = mapped_column(String(64))
    target_status: Mapped[str | None] = mapped_column(String(64))
    dedupe_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_body: Mapped[str] = mapped_column(Text, nullable=False)
    source_ip: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[WebhookInboxStatus] = mapped_column(
        String(20),
        nullable=False,
        default=WebhookInboxStatus.PENDING,
        server_default="PENDING",
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    claim_token: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    claimed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_code: Mapped[str | None] = mapped_column(String(128))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OutboxEventModel(Base):
    """Transactional outbox event pending delivery to RabbitMQ."""

    __tablename__ = "outbox_events"
    __table_args__ = (Index("ix_outbox_events_status_created_at", "status", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid7)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="pending"
    )
    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    claim_token: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    claimed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProcessedEventModel(Base):
    __tablename__ = "processed_events"

    event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    routing_key: Mapped[str] = mapped_column(String(255), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
