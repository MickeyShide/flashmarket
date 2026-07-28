from dataclasses import dataclass

from auth_service.models import LoginSession, User


@dataclass(frozen=True, slots=True)
class IssuedTokens:
    access_token: str
    refresh_token: str
    access_expires_in: int


@dataclass(frozen=True, slots=True)
class AuthenticationResult:
    user: User
    session: LoginSession
    tokens: IssuedTokens


@dataclass(frozen=True, slots=True)
class RefreshResult:
    user: User
    session: LoginSession
    tokens: IssuedTokens
