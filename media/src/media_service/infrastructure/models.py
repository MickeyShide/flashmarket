"""SQLAlchemy models for Media."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Enum, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from media_service.domain.entities import AssetStatus, Visibility
from media_service.infrastructure.database import Base, utc_now


class MediaAssetModel(Base):
    """Persistent metadata and lifecycle for one S3 object."""

    __tablename__ = "media_assets"
    __table_args__ = (
        CheckConstraint("expected_size > 0", name="ck_media_expected_size_positive"),
        CheckConstraint(
            "actual_size IS NULL OR actual_size > 0",
            name="ck_media_actual_size_positive",
        ),
        Index("ix_media_uploader_created", "uploader_id", "created_at"),
        Index("ix_media_entity", "entity_type", "entity_id", "purpose", "status"),
        Index("ix_media_expiration", "status", "upload_expires_at"),
        Index("ix_media_deletion", "status", "delete_requested_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid7)
    uploader_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    purpose: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(64))
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    status: Mapped[AssetStatus] = mapped_column(
        Enum(AssetStatus, native_enum=False, length=32), nullable=False, default=AssetStatus.PENDING
    )
    visibility: Mapped[Visibility] = mapped_column(
        Enum(Visibility, native_enum=False, length=16), nullable=False, default=Visibility.PUBLIC
    )
    bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    object_key: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    declared_content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    detected_content_type: Mapped[str | None] = mapped_column(String(255))
    expected_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    actual_size: Mapped[int | None] = mapped_column(BigInteger)
    sha256: Mapped[str | None] = mapped_column(String(64))
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    upload_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delete_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
