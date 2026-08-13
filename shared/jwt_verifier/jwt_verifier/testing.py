"""Testing utilities for local JWT verification."""

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


class TestKeyStore:
    """Helper to generate temporary Ed25519 keys and signed JWT tokens for unit/integration tests."""

    __test__ = False

    def __init__(self, key_dir: Path, key_id: str = "test-key") -> None:
        self.key_dir = key_dir
        self.key_id = key_id
        self.private_key = Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        self._write_public_key()

    def _write_public_key(self) -> None:
        self.key_dir.mkdir(parents=True, exist_ok=True)
        pub_pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        (self.key_dir / f"{self.key_id}.pem").write_bytes(pub_pem)

    def create_token(
        self,
        user_id: uuid.UUID | str | None = None,
        role: str = "ADMIN",
        session_id: uuid.UUID | str | None = None,
        iss: str = "flashmarket-auth",
        aud: str = "flashmarket-api",
        expires_in_seconds: int = 3600,
    ) -> str:
        """Create a signed access token."""
        uid = str(user_id or uuid.uuid7())
        sid = str(session_id or uuid.uuid7())
        now = datetime.now(UTC)
        payload = {
            "sub": uid,
            "sid": sid,
            "role": role,
            "type": "access",
            "jti": str(uuid.uuid7()),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=expires_in_seconds)).timestamp()),
            "iss": iss,
            "aud": aud,
        }
        headers = {"alg": "EdDSA", "typ": "JWT", "kid": self.key_id}
        return jwt.encode(payload, self.private_key, algorithm="EdDSA", headers=headers)
