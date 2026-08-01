import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from jwt_verifier.exceptions import ExpiredTokenError, InvalidTokenError, KeyStoreError
from jwt_verifier.models import Principal


class JWTVerifier:
    """Read-only local JWT verifier for downstream services."""

    def __init__(
        self,
        public_key_dir: Path | str,
        algorithm: str = "EdDSA",
        issuer: str = "flashmarket-auth",
        audience: str = "flashmarket-api",
    ) -> None:
        self.public_key_dir = Path(public_key_dir)
        self.algorithm = algorithm
        self.issuer = issuer
        self.audience = audience
        self._keys_cache: dict[str, Ed25519PublicKey] = {}
        self._loaded = False

    def validate_startup(self) -> None:
        """Validate public key directory at service startup."""
        if not self.public_key_dir.exists() or not self.public_key_dir.is_dir():
            return
        try:
            self._load_keys()
        except KeyStoreError:
            pass

    def _load_keys(self) -> None:
        """Scan directory and load all *.pem Ed25519 public keys into memory cache."""
        if not self.public_key_dir.exists() or not self.public_key_dir.is_dir():
            raise KeyStoreError(
                f"Public key directory {self.public_key_dir} does not exist"
            )

        keys: dict[str, Ed25519PublicKey] = {}
        pem_files = list(self.public_key_dir.glob("*.pem"))
        if not pem_files:
            raise KeyStoreError(
                f"Public key directory {self.public_key_dir} contains no .pem files"
            )

        for pem_path in pem_files:
            try:
                raw_bytes = pem_path.read_bytes()
                key = serialization.load_pem_public_key(raw_bytes)
                if not isinstance(key, Ed25519PublicKey):
                    raise KeyStoreError(
                        f"Key file {pem_path.name} is not an Ed25519 public key"
                    )
                keys[pem_path.stem] = key
            except KeyStoreError:
                raise
            except Exception as exc:
                raise KeyStoreError(
                    f"Failed to load public key from {pem_path.name}: {exc}"
                ) from exc

        if not keys:
            raise KeyStoreError(
                f"No valid Ed25519 public keys could be loaded from {self.public_key_dir}"
            )

        self._keys_cache = keys
        self._loaded = True

    def get_public_key(self, kid: str) -> Ed25519PublicKey:
        """Get public key by kid, reloading directory once if kid is unknown."""
        if not self._loaded:
            self._load_keys()

        if kid in self._keys_cache:
            return self._keys_cache[kid]

        # Unknown kid: rescan directory once
        self._load_keys()

        if kid in self._keys_cache:
            return self._keys_cache[kid]

        raise InvalidTokenError(f"Unknown JWT signing key kid: {kid}")

    def decode_and_verify(self, token: str) -> Principal:
        """Verify an access token and return an immutable Principal."""
        try:
            unverified_header = jwt.get_unverified_header(token)
        except Exception as exc:
            raise InvalidTokenError("Malformed JWT header") from exc

        if unverified_header.get("typ") != "JWT":
            raise InvalidTokenError("Header typ must be 'JWT'")

        alg = unverified_header.get("alg")
        if alg != self.algorithm:
            raise InvalidTokenError(f"Unsupported algorithm '{alg}', expected '{self.algorithm}'")

        kid = unverified_header.get("kid")
        if not kid or not isinstance(kid, str):
            raise InvalidTokenError("Missing or invalid 'kid' in header")

        public_key = self.get_public_key(kid)

        try:
            payload: dict[str, Any] = jwt.decode(
                token,
                key=public_key,
                algorithms=[self.algorithm],
                issuer=self.issuer,
                audience=self.audience,
                options={
                    "require": ["sub", "sid", "role", "type", "jti", "iat", "exp"],
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_iss": True,
                    "verify_aud": True,
                },
            )
        except jwt.ExpiredSignatureError as exc:
            raise ExpiredTokenError("Access token has expired") from exc
        except jwt.PyJWTError as exc:
            raise InvalidTokenError(f"JWT verification failed: {exc}") from exc

        if payload.get("type") != "access":
            raise InvalidTokenError("Unexpected token type, expected 'access'")

        role = payload.get("role")
        if role not in ("CUSTOMER", "ADMIN"):
            raise InvalidTokenError(f"Unknown role '{role}'")

        try:
            user_id = uuid.UUID(str(payload["sub"]))
            session_id = uuid.UUID(str(payload["sid"]))
            token_id = uuid.UUID(str(payload["jti"]))
        except (ValueError, TypeError) as exc:
            raise InvalidTokenError("Invalid UUID format in sub, sid, or jti claim") from exc

        try:
            exp_ts = float(payload["exp"])
            expires_at = datetime.fromtimestamp(exp_ts, UTC)
        except (ValueError, TypeError) as exc:
            raise InvalidTokenError("Invalid exp timestamp") from exc

        return Principal(
            user_id=user_id,
            session_id=session_id,
            token_id=token_id,
            role=role,
            expires_at=expires_at,
        )
