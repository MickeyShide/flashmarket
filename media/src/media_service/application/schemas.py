"""Pydantic API contracts for Media."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from media_service.domain.entities import AssetStatus, Visibility


class CreateUploadRequest(BaseModel):
    purpose: str = Field(min_length=2, max_length=64)
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=3, max_length=255)
    size: int = Field(ge=1)
    entity_type: str | None = Field(default=None, max_length=64)
    entity_id: UUID | None = None

    @field_validator("content_type")
    @classmethod
    def normalize_content_type(cls, value: str) -> str:
        return value.strip().lower()


class BindingRequest(BaseModel):
    entity_type: str | None = Field(default=None, max_length=64)
    entity_id: UUID | None = None


class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    uploader_id: UUID
    purpose: str
    entity_type: str | None
    entity_id: UUID | None
    status: AssetStatus
    visibility: Visibility
    original_filename: str
    content_type: str
    size: int
    sha256: str | None
    width: int | None
    height: int | None
    public_url: str | None
    upload_expires_at: datetime
    uploaded_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PresignedUploadResponse(BaseModel):
    method: Literal["POST"] = "POST"
    url: str
    fields: dict[str, str]
    expires_at: datetime


class CreateUploadResponse(BaseModel):
    asset: AssetResponse
    upload: PresignedUploadResponse
    complete_url: str


class AssetListResponse(BaseModel):
    items: list[AssetResponse]
    total: int
    limit: int
    offset: int


class AssetListParams(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    purpose: str | None = Field(default=None, max_length=64)
    status: AssetStatus | None = None
