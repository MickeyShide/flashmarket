import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from jwt_verifier import (
    ExpiredTokenError,
    InvalidTokenError,
    JWTVerifier,
    KeyStoreError,
)


@pytest.fixture
def key_pair() -> tuple[Ed25519PrivateKey, Ed25519PublicKey]:
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    return priv, pub


@pytest.fixture
def keys_dir(tmp_path: Path, key_pair: tuple[Ed25519PrivateKey, Ed25519PublicKey]) -> Path:
    _, pub = key_pair
    pub_dir = tmp_path / "public"
    pub_dir.mkdir()
    pub_pem = pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    (pub_dir / "key1.pem").write_bytes(pub_pem)
    return pub_dir


def create_token(
    priv_key: Ed25519PrivateKey,
    kid: str = "key1",
    sub: str | None = None,
    sid: str | None = None,
    role: str = "CUSTOMER",
    token_type: str = "access",
    iss: str = "flashmarket-auth",
    aud: str = "flashmarket-api",
    alg: str = "EdDSA",
    typ: str = "JWT",
    expired: bool = False,
    missing_claim: str | None = None,
    invalid_uuid: bool = False,
) -> str:
    now = datetime.now(UTC)
    exp = now - timedelta(minutes=5) if expired else now + timedelta(minutes=5)
    payload = {
        "sub": "not-a-uuid" if invalid_uuid else str(sub or uuid.uuid7()),
        "sid": str(sid or uuid.uuid7()),
        "role": role,
        "type": token_type,
        "jti": str(uuid.uuid7()),
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "iss": iss,
        "aud": aud,
    }
    if missing_claim:
        payload.pop(missing_claim, None)

    headers = {}
    if typ is not None:
        headers["typ"] = typ
    if alg is not None:
        headers["alg"] = alg
    if kid is not None:
        headers["kid"] = kid

    return jwt.encode(payload, priv_key, algorithm=alg, headers=headers)


def test_valid_customer_and_admin_tokens(
    key_pair: tuple[Ed25519PrivateKey, Ed25519PublicKey], keys_dir: Path
) -> None:
    priv, _ = key_pair
    verifier = JWTVerifier(public_key_dir=keys_dir)
    verifier.validate_startup()

    customer_user = uuid.uuid7()
    cust_token = create_token(priv, sub=str(customer_user), role="CUSTOMER")
    p1 = verifier.decode_and_verify(cust_token)
    assert p1.user_id == customer_user
    assert p1.role == "CUSTOMER"

    admin_user = uuid.uuid7()
    admin_token = create_token(priv, sub=str(admin_user), role="ADMIN")
    p2 = verifier.decode_and_verify(admin_token)
    assert p2.user_id == admin_user
    assert p2.role == "ADMIN"


def test_malformed_jwt_and_headers(
    key_pair: tuple[Ed25519PrivateKey, Ed25519PublicKey], keys_dir: Path
) -> None:
    priv, _ = key_pair
    verifier = JWTVerifier(public_key_dir=keys_dir)

    with pytest.raises(InvalidTokenError):
        verifier.decode_and_verify("not.a.valid.jwt")

    bad_typ = create_token(priv, typ="BAD")
    with pytest.raises(InvalidTokenError):
        verifier.decode_and_verify(bad_typ)

    bad_alg = jwt.encode(
        {"sub": str(uuid.uuid7()), "type": "access", "role": "CUSTOMER"},
        "test-only-hmac-key-at-least-32-bytes-long",
        algorithm="HS256",
        headers={"kid": "key1"},
    )
    with pytest.raises(InvalidTokenError):
        verifier.decode_and_verify(bad_alg)


def test_wrong_signature_and_claims(
    key_pair: tuple[Ed25519PrivateKey, Ed25519PublicKey], keys_dir: Path
) -> None:
    priv, _ = key_pair
    other_priv = Ed25519PrivateKey.generate()
    verifier = JWTVerifier(public_key_dir=keys_dir)

    # Wrong signature
    token_wrong_sig = create_token(other_priv, kid="key1")
    with pytest.raises(InvalidTokenError):
        verifier.decode_and_verify(token_wrong_sig)

    # Wrong issuer
    token_bad_iss = create_token(priv, iss="wrong-issuer")
    with pytest.raises(InvalidTokenError):
        verifier.decode_and_verify(token_bad_iss)

    # Wrong audience
    token_bad_aud = create_token(priv, aud="wrong-audience")
    with pytest.raises(InvalidTokenError):
        verifier.decode_and_verify(token_bad_aud)

    # Wrong token type
    token_refresh = create_token(priv, token_type="refresh")
    with pytest.raises(InvalidTokenError):
        verifier.decode_and_verify(token_refresh)

    # Unknown role
    token_unknown_role = create_token(priv, role="SUPERUSER")
    with pytest.raises(InvalidTokenError):
        verifier.decode_and_verify(token_unknown_role)

    # Invalid UUID
    token_bad_uuid = create_token(priv, invalid_uuid=True)
    with pytest.raises(InvalidTokenError):
        verifier.decode_and_verify(token_bad_uuid)


def test_missing_claims(
    key_pair: tuple[Ed25519PrivateKey, Ed25519PublicKey], keys_dir: Path
) -> None:
    priv, _ = key_pair
    verifier = JWTVerifier(public_key_dir=keys_dir)

    for claim in ["sub", "sid", "role", "type", "jti", "iat", "exp"]:
        tok = create_token(priv, missing_claim=claim)
        with pytest.raises(InvalidTokenError):
            verifier.decode_and_verify(tok)


def test_expired_token(
    key_pair: tuple[Ed25519PrivateKey, Ed25519PublicKey], keys_dir: Path
) -> None:
    priv, _ = key_pair
    verifier = JWTVerifier(public_key_dir=keys_dir)
    expired_tok = create_token(priv, expired=True)
    with pytest.raises(ExpiredTokenError):
        verifier.decode_and_verify(expired_tok)


def test_unknown_kid_and_dynamic_reload(
    key_pair: tuple[Ed25519PrivateKey, Ed25519PublicKey], keys_dir: Path
) -> None:
    priv1, _ = key_pair
    verifier = JWTVerifier(public_key_dir=keys_dir)
    verifier.validate_startup()

    # Unknown kid initially
    priv2 = Ed25519PrivateKey.generate()
    pub2 = priv2.public_key()
    tok2 = create_token(priv2, kid="key2")

    with pytest.raises(InvalidTokenError):
        verifier.decode_and_verify(tok2)

    # Publish key2 to keys_dir
    pub2_pem = pub2.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    (keys_dir / "key2.pem").write_bytes(pub2_pem)

    # Verifier rescans and verifies tok2 successfully
    p2 = verifier.decode_and_verify(tok2)
    assert p2 is not None

    # Still accepts key1 tokens
    tok1 = create_token(priv1, kid="key1")
    p1 = verifier.decode_and_verify(tok1)
    assert p1 is not None


def test_keystore_startup_failures(tmp_path: Path) -> None:
    # Non-existent dir
    v1 = JWTVerifier(public_key_dir=tmp_path / "nonexistent")
    with pytest.raises(KeyStoreError):
        v1.validate_startup()

    # Empty dir
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    v2 = JWTVerifier(public_key_dir=empty_dir)
    with pytest.raises(KeyStoreError):
        v2.validate_startup()

    # Non-pem file
    bad_file_dir = tmp_path / "bad"
    bad_file_dir.mkdir()
    (bad_file_dir / "key.pem").write_text("NOT A PEM KEY")
    v3 = JWTVerifier(public_key_dir=bad_file_dir)
    with pytest.raises(KeyStoreError):
        v3.validate_startup()
