"""SQLAlchemy ORM models for the wishlist database."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from wishlist.infrastructure.database import Base, utc_now


class WishlistItemModel(Base):
    """Stores items added to user's wishlist."""

    __tablename__ = "wishlist_items"
    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uq_wishlist_user_product"),
        Index("ix_wishlist_items_user_created", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid7)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
