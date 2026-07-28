import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from auth_service.models import UserRole


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RegisterRequest(StrictSchema):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    full_name: str | None = Field(default=None, min_length=1, max_length=120)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        """Validate password."""
        if value.isspace():
            raise ValueError("Password cannot contain only whitespace")
        return value

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str | None) -> str | None:
        """Normalize full name."""
        if value is None:
            return None
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Full name cannot be empty")
        return normalized


class LoginRequest(StrictSchema):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(StrictSchema):
    refresh_token: str | None = Field(default=None, min_length=32, max_length=256)


class IntrospectionRequest(StrictSchema):
    token: str = Field(min_length=32, max_length=4096)


class IntrospectionResponse(BaseModel):
    active: bool
    sub: uuid.UUID | None = None
    sid: uuid.UUID | None = None
    role: UserRole | None = None
    exp: datetime | None = None
    iss: str | None = None
    aud: str | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str | None = None
    csrf_token: str | None = None
    token_type: str = "bearer"
    access_expires_in: int


class AuthResponse(BaseModel):
    user: UserResponse
    tokens: TokenPair


class TokenRefreshResponse(BaseModel):
    tokens: TokenPair


class MessageResponse(BaseModel):
    message: str


class ProfileUpdateRequest(StrictSchema):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str | None) -> str | None:
        """Normalize full name."""
        if value is None:
            return None
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Full name cannot be empty")
        return normalized


class PasswordChangeRequest(StrictSchema):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        """Validate new password."""
        if value.isspace():
            raise ValueError("Password cannot contain only whitespace")
        return value


class SessionResponse(BaseModel):
    id: uuid.UUID
    current: bool
    user_agent: str | None
    ip_address: str | None
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    revoked_at: datetime | None
    active: bool


class RoleUpdateRequest(StrictSchema):
    role: UserRole


class AccountStatusUpdateRequest(StrictSchema):
    is_active: bool


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    limit: int
    offset: int


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_type: str
    actor_user_id: uuid.UUID | None
    subject_user_id: uuid.UUID | None
    ip_address: str | None
    user_agent: str | None
    request_id: str | None
    event_data: dict[str, object] | None
    created_at: datetime


class AuditEventListResponse(BaseModel):
    items: list[AuditEventResponse]
    total: int
    limit: int
    offset: int
