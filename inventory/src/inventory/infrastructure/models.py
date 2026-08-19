"""SQLAlchemy ORM models for the inventory database."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from inventory.domain.entities import ReservationStatus
from inventory.infrastructure.database import Base, utc_now


class StockModel(Base):
    """Available, reserved and sold units for a product or variant."""

    __tablename__ = "stocks"
    __table_args__ = (
        CheckConstraint("total >= 0", name="ck_stocks_total_non_negative"),
        CheckConstraint("available >= 0", name="ck_stocks_available_non_negative"),
        CheckConstraint("reserved >= 0", name="ck_stocks_reserved_non_negative"),
        CheckConstraint("sold >= 0", name="ck_stocks_sold_non_negative"),
        CheckConstraint(
            "reserved + sold <= total",
            name="ck_stocks_reservation_invariant",
        ),
        UniqueConstraint(
            "product_id",
            "variant_id",
            name="uq_stocks_product_variant",
            postgresql_nulls_not_distinct=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid7)
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    variant_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    available: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sold: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    reservations: Mapped[list[ReservationModel]] = relationship(
        back_populates="stock",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ReservationModel.created_at",
        lazy="selectin",
    )


class ReservationModel(Base):
    """A temporary reservation of stock for a user."""

    __tablename__ = "reservations"
    __table_args__ = (
        Index(
            "ix_reservations_status_expires_at",
            "status",
            "expires_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid7)
    stock_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stocks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[ReservationStatus] = mapped_column(
        String(20),
        nullable=False,
        default=ReservationStatus.RESERVED,
        server_default="RESERVED",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    drop_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    stock: Mapped[StockModel] = relationship(back_populates="reservations")


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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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


class ProcessedEventModel(Base):
    """Inbox deduplication marker committed with consumer side effects."""

    __tablename__ = "processed_events"

    event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    routing_key: Mapped[str] = mapped_column(String(255), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
