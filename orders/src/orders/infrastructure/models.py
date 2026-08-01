"""SQLAlchemy ORM models for the orders database."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from orders.domain.entities import DiscountType, OrderStatus, PromocodeStatus
from orders.infrastructure.database import Base, utc_now


class OrderModel(Base):
    """Customer order with embedded product snapshot."""

    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_orders_quantity_positive"),
        CheckConstraint("price > 0", name="ck_orders_price_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid7)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="RUB")
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        String(20),
        nullable=False,
        default=OrderStatus.PENDING,
        server_default="PENDING",
    )
    reservation_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    payment_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    checkout_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    variant_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    variant_sku: Mapped[str | None] = mapped_column(String(100), nullable=True)
    variant_size: Mapped[str | None] = mapped_column(String(20), nullable=True)
    variant_color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    drop_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    payment_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Promocode and discount fields
    original_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0"), server_default="0"
    )
    final_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    promocode_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("promocodes.id"), nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


class PromocodeModel(Base):
    """Promocode definition model."""

    __tablename__ = "promocodes"
    __table_args__ = (
        CheckConstraint("discount_value > 0", name="ck_promocodes_value_positive"),
        CheckConstraint("current_uses >= 0", name="ck_promocodes_uses_non_negative"),
        CheckConstraint("expires_at > starts_at", name="ck_promocodes_valid_period"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid7)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    discount_type: Mapped[DiscountType] = mapped_column(String(20), nullable=False)
    discount_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="RUB")
    min_order_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    max_discount_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_uses_per_user: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    current_uses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[PromocodeStatus] = mapped_column(
        String(20), nullable=False, default=PromocodeStatus.ACTIVE
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class PromocodeUsageModel(Base):
    """Record of a user applying a promocode to an order."""

    __tablename__ = "promocode_usages"
    __table_args__ = (
        UniqueConstraint("promocode_id", "order_id", name="uq_usage_promocode_order"),
        Index("ix_usage_promocode_user", "promocode_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid7)
    promocode_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("promocodes.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    order_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, unique=True)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


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
