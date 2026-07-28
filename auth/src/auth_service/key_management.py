import base64
import os
import shutil
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from auth_service.config import get_settings


@dataclass(frozen=True)
class SigningKeyRing:
    active_key_id: str
    signing_key: Ed25519PrivateKey
    verification_keys: dict[str, Ed25519PublicKey]

    def verification_key(self, key_id: str) -> Ed25519PublicKey:
        try:
            return self.verification_keys[key_id]
        except KeyError as exc:
            raise jwt.InvalidTokenError("Unknown JWT signing key") from exc

    def public_jwks(self) -> list[dict[str, str]]:
        return [
            public_key_to_jwk(key_id, key) for key_id, key in sorted(self.verification_keys.items())
        ]


def _write_new_file(path: Path, content: bytes, mode: int) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    with os.fdopen(descriptor, "wb") as file:
        file.write(content)


def _migrate_legacy_key_pair(output_directory: Path, key_id: str) -> tuple[Path, Path] | None:
    legacy_private = output_directory / "jwt_private.pem"
    legacy_public = output_directory / "jwt_public.pem"
    if not legacy_private.exists() and not legacy_public.exists():
        return None
    if not legacy_private.exists() or not legacy_public.exists():
        raise FileExistsError(
            "Only one legacy JWT key exists; repair or remove the incomplete pair"
        )

    validate_key_pair(legacy_private, legacy_public)
    private_path = output_directory / "private" / f"{key_id}.pem"
    public_path = output_directory / "public" / f"{key_id}.pem"
    private_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    if private_path.exists() or public_path.exists():
        return None

    shutil.copyfile(legacy_private, private_path)
    shutil.copyfile(legacy_public, public_path)
    private_path.chmod(0o600)
    public_path.chmod(0o644)
    return private_path, public_path


def generate_jwt_key_pair(
    output_directory: Path,
    *,
    key_id: str | None = None,
    force: bool = False,
) -> tuple[Path, Path]:
    resolved_key_id = key_id or get_settings().jwt_key_id
    allowed_characters = frozenset(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-"
    )
    if not resolved_key_id or any(char not in allowed_characters for char in resolved_key_id):
        raise ValueError(
            "JWT key id may contain only letters, digits, dots, underscores and hyphens"
        )

    output_directory.mkdir(parents=True, exist_ok=True)
    private_directory = output_directory / "private"
    public_directory = output_directory / "public"
    private_directory.mkdir(parents=True, exist_ok=True)
    public_directory.mkdir(parents=True, exist_ok=True)
    private_path = private_directory / f"{resolved_key_id}.pem"
    public_path = public_directory / f"{resolved_key_id}.pem"

    if not force:
        migrated = _migrate_legacy_key_pair(output_directory, resolved_key_id)
        if migrated is not None:
            return migrated

    if private_path.exists() or public_path.exists():
        if private_path.exists() and public_path.exists() and not force:
            validate_key_pair(private_path, public_path)
            return private_path, public_path
        if not force:
            raise FileExistsError(
                "Only one JWT key exists. Remove the incomplete pair or run with --force."
            )
        private_path.unlink(missing_ok=True)
        public_path.unlink(missing_ok=True)

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    try:
        _write_new_file(private_path, private_pem, 0o600)
        _write_new_file(public_path, public_pem, 0o644)
    except Exception:
        private_path.unlink(missing_ok=True)
        public_path.unlink(missing_ok=True)
        raise
    return private_path, public_path


@lru_cache
def load_private_key(path: Path) -> Ed25519PrivateKey:
    try:
        key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    except (OSError, ValueError) as exc:
        raise ValueError(f"Cannot load Ed25519 private key from {path}") from exc
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError(f"JWT private key at {path} is not an Ed25519 key")
    return key


@lru_cache
def load_public_key(path: Path) -> Ed25519PublicKey:
    try:
        key = serialization.load_pem_public_key(path.read_bytes())
    except (OSError, ValueError) as exc:
        raise ValueError(f"Cannot load Ed25519 public key from {path}") from exc
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError(f"JWT public key at {path} is not an Ed25519 key")
    return key


def validate_key_pair(private_path: Path, public_path: Path) -> None:
    private_public_key = load_private_key(private_path).public_key()
    configured_public_key = load_public_key(public_path)
    private_public_bytes = private_public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    configured_public_bytes = configured_public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    if private_public_bytes != configured_public_bytes:
        raise ValueError("Configured JWT private and public keys do not form a pair")


@lru_cache
def load_signing_key_ring(keys_directory: Path, active_key_id: str) -> SigningKeyRing:
    private_path = keys_directory / "private" / f"{active_key_id}.pem"
    public_directory = keys_directory / "public"
    signing_key = load_private_key(private_path)
    verification_keys = {
        path.stem: load_public_key(path)
        for path in public_directory.glob("*.pem")
        if path.is_file()
    }
    if active_key_id not in verification_keys:
        raise ValueError(f"Active JWT public key {active_key_id!r} is missing")
    validate_key_pair(private_path, public_directory / f"{active_key_id}.pem")
    return SigningKeyRing(
        active_key_id=active_key_id,
        signing_key=signing_key,
        verification_keys=verification_keys,
    )


def get_signing_key_ring() -> SigningKeyRing:
    settings = get_settings()
    return load_signing_key_ring(settings.jwt_keys_directory, settings.jwt_key_id)


def validate_configured_key_pair() -> None:
    get_signing_key_ring()


def get_private_signing_key() -> Ed25519PrivateKey:
    return get_signing_key_ring().signing_key


def get_public_verification_key(key_id: str | None = None) -> Ed25519PublicKey:
    key_ring = get_signing_key_ring()
    return key_ring.verification_key(key_id or key_ring.active_key_id)


def public_key_to_jwk(key_id: str, public_key: Ed25519PublicKey) -> dict[str, str]:
    settings = get_settings()
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    encoded_key = base64.urlsafe_b64encode(public_bytes).rstrip(b"=").decode("ascii")
    return {
        "kty": "OKP",
        "crv": "Ed25519",
        "x": encoded_key,
        "use": "sig",
        "alg": settings.jwt_algorithm,
        "kid": key_id,
    }


def get_public_jwks() -> list[dict[str, str]]:
    return get_signing_key_ring().public_jwks()


def get_public_jwk() -> dict[str, str]:
    return public_key_to_jwk(get_signing_key_ring().active_key_id, get_public_verification_key())
