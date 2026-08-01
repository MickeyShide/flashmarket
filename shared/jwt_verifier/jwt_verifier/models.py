import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

UserRole = Literal["CUSTOMER", "ADMIN"]


@dataclass(frozen=True)
class Principal:
    user_id: uuid.UUID
    session_id: uuid.UUID
    token_id: uuid.UUID
    role: str
    expires_at: datetime
