from fastapi import APIRouter

from auth_service.key_management import get_public_jwks

router = APIRouter(tags=["well-known"])


@router.get("/.well-known/jwks.json")
async def json_web_key_set() -> dict[str, list[dict[str, str]]]:
    """Expose public JWT verification keys as JWKS."""
    return {"keys": get_public_jwks()}
