import uuid
from pathlib import Path

import jwt
from httpx import AsyncClient

from auth_service.config import get_settings
from auth_service.key_management import (
    generate_jwt_key_pair,
    get_public_jwks,
    get_public_verification_key,
    load_signing_key_ring,
)
from auth_service.models import User, UserRole
from auth_service.security import create_access_token, decode_access_token
from tests.test_auth import register_user


async def test_access_token_uses_ed25519_and_public_jwks(
    client: AsyncClient,
) -> None:
    registered = await register_user(client)
    access_token = registered["tokens"]["access_token"]
    settings = get_settings()

    header = jwt.get_unverified_header(access_token)
    assert header["alg"] == "EdDSA"
    assert header["kid"] == settings.jwt_key_id

    payload = jwt.decode(
        access_token,
        get_public_verification_key(),
        algorithms=["EdDSA"],
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )
    assert payload["sub"] == registered["user"]["id"]
    assert payload["type"] == "access"
    assert set(payload) == {
        "sub",
        "sid",
        "role",
        "type",
        "jti",
        "iat",
        "exp",
        "iss",
        "aud",
    }

    response = await client.get("/.well-known/jwks.json")
    assert response.status_code == 200
    jwk = response.json()["keys"][0]
    assert jwk == {
        "kty": "OKP",
        "crv": "Ed25519",
        "x": jwk["x"],
        "use": "sig",
        "alg": "EdDSA",
        "kid": settings.jwt_key_id,
    }
    assert "d" not in jwk


def test_key_rotation_keeps_tokens_from_previous_public_key_valid(
    tmp_path: Path,
) -> None:
    settings = get_settings()
    previous_directory = settings.jwt_keys_directory
    previous_key_id = settings.jwt_key_id
    first_key_id = "rotation-v1"
    second_key_id = "rotation-v2"
    generate_jwt_key_pair(tmp_path, key_id=first_key_id)
    generate_jwt_key_pair(tmp_path, key_id=second_key_id)
    user = User(
        id=uuid.uuid7(),
        email="rotation@example.com",
        password_hash="not-used",
        role=UserRole.CUSTOMER,
    )
    session_id = uuid.uuid7()

    try:
        settings.jwt_keys_directory = tmp_path
        settings.jwt_key_id = first_key_id
        load_signing_key_ring.cache_clear()
        old_token, _ = create_access_token(user, session_id)

        settings.jwt_key_id = second_key_id
        load_signing_key_ring.cache_clear()
        new_token, _ = create_access_token(user, session_id)

        assert jwt.get_unverified_header(old_token)["kid"] == first_key_id
        assert jwt.get_unverified_header(new_token)["kid"] == second_key_id
        assert decode_access_token(old_token).user_id == user.id
        assert decode_access_token(new_token).user_id == user.id
        assert {key["kid"] for key in get_public_jwks()} == {
            first_key_id,
            second_key_id,
        }
    finally:
        settings.jwt_keys_directory = previous_directory
        settings.jwt_key_id = previous_key_id
        load_signing_key_ring.cache_clear()
