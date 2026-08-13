"""SQLAlchemy ORM models for the drops database."""

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

from drops.domain.entities import DropStatus
from drops.infrastructure.database import Base, utc_now


class DropModel(Base):
    """Flash-sale drop campaign model."""

    __tablename__ = "drops"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="ck_drops_valid_time_range"),
        CheckConstraint("max_per_user >= 1", name="ck_drops_max_per_user_positive"),
        CheckConstraint("payment_timeout_seconds >= 60", name="ck_drops_payment_timeout_min"),
        Index("ix_drops_status", "status"),
        Index("ix_drops_starts_at", "starts_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid7)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    cover_image: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=DropStatus.DRAFT)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    max_per_user: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    payment_timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    items: Mapped[list[DropItemModel]] = relationship(
        back_populates="drop", cascade="all, delete-orphan", lazy="selectin"
    )


class DropItemModel(Base):
    """Product associated with a flash-sale drop."""

    __tablename__ = "drop_items"
    __table_args__ = (UniqueConstraint("drop_id", "product_id", name="uq_drop_items_drop_product"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid7)
    drop_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("drops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    drop: Mapped[DropModel] = relationship(back_populates="items")


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
