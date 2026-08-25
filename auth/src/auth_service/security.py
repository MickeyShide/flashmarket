import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from argon2.low_level import Type

from auth_service.config import get_settings
from auth_service.key_management import get_signing_key_ring
from auth_service.models import User, UserRole
from auth_service.time import utc_now

password_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65_536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)
DUMMY_PASSWORD_HASH = password_hasher.hash("not-the-password-used-by-any-account")


@dataclass(frozen=True)
class AccessTokenClaims:
    user_id: uuid.UUID
    session_id: uuid.UUID
    role: UserRole
    token_id: uuid.UUID
    expires_at: datetime


def hash_password(password: str) -> str:
    """Hash a password with Argon2."""
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its Argon2 hash."""
    try:
        return password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    """Report whether an Argon2 hash needs upgrading."""
    try:
        return password_hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return False


def burn_password_check(password: str) -> None:
    """Perform a dummy password check to equalize timing."""
    verify_password(password, DUMMY_PASSWORD_HASH)


def create_access_token(user: User, session_id: uuid.UUID) -> tuple[str, int]:
    """Create a signed access token for one session."""
    settings = get_settings()
    key_ring = get_signing_key_ring()
    now = utc_now()
    expires_in = settings.access_token_ttl_minutes * 60
    payload = {
        "sub": str(user.id),
        "sid": str(session_id),
        "role": user.role.value,
        "type": "access",
        "jti": str(uuid.uuid7()),
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    token = jwt.encode(
        payload,
        key_ring.signing_key,
        algorithm=settings.jwt_algorithm,
        headers={
            "kid": key_ring.active_key_id,
            "typ": "JWT",
        },
    )
    return token, expires_in


def decode_access_token(token: str) -> AccessTokenClaims:
    """Validate and decode an access token."""
    settings = get_settings()
    key_ring = get_signing_key_ring()
    header = jwt.get_unverified_header(token)
    if header.get("alg") != settings.jwt_algorithm:
        raise jwt.InvalidTokenError("Unexpected JWT signing algorithm")
    key_id = header.get("kid")
    if not isinstance(key_id, str):
        raise jwt.InvalidTokenError("Missing JWT signing key id")
    payload = jwt.decode(
        token,
        key_ring.verification_key(key_id),
        algorithms=[settings.jwt_algorithm],
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        options={"require": ["sub", "sid", "role", "type", "jti", "iat", "exp"]},
    )
    if payload["type"] != "access":
        raise jwt.InvalidTokenError("Unexpected token type")
    try:
        return AccessTokenClaims(
            user_id=uuid.UUID(payload["sub"]),
            session_id=uuid.UUID(payload["sid"]),
            role=UserRole(payload["role"]),
            token_id=uuid.UUID(payload["jti"]),
            expires_at=datetime.fromtimestamp(payload["exp"], UTC),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise jwt.InvalidTokenError("Invalid access token claims") from exc


def generate_refresh_token() -> tuple[str, str]:
    """Create a refresh token and its stored digest."""
    raw_token = secrets.token_urlsafe(64)
    return raw_token, digest_refresh_token(raw_token)


def digest_refresh_token(raw_token: str) -> str:
    """Return the SHA-256 digest stored for a refresh token."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
