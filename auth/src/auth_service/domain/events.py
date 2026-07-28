import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType

from auth_service.time import utc_now

type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]


class EventType(StrEnum):
    USER_REGISTERED = "user_registered"
    USER_LOGGED_IN = "user_logged_in"
    TOKEN_REFRESHED = "token_refreshed"
    REFRESH_TOKEN_REUSE = "refresh_token_reuse"
    USER_LOGGED_OUT = "user_logged_out"
    PROFILE_UPDATED = "profile_updated"
    PASSWORD_CHANGED = "password_changed"
    USER_ROLE_CHANGED = "user_role_changed"
    USER_STATUS_CHANGED = "user_status_changed"
    SESSION_REVOKED = "session_revoked"
    ALL_SESSIONS_REVOKED = "all_sessions_revoked"


@dataclass(frozen=True, slots=True)
class DomainEvent:
    event_type: EventType
    aggregate_type: str
    aggregate_id: uuid.UUID
    payload: dict[str, JsonValue] = field(default_factory=dict)
    event_id: uuid.UUID = field(default_factory=uuid.uuid7)
    occurred_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))

    def message_payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": 1,
            "event_id": str(self.event_id),
            "event_type": self.event_type.value,
            "occurred_at": self.occurred_at.isoformat(),
            "aggregate": {
                "type": self.aggregate_type,
                "id": str(self.aggregate_id),
            },
            "data": dict(self.payload),
        }
