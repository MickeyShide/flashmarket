from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from jwt_verifier.exceptions import ExpiredTokenError, InvalidTokenError
from jwt_verifier.models import Principal
from jwt_verifier.verifier import JWTVerifier

bearer_scheme = HTTPBearer(auto_error=False)


class JWTAuth:
    """FastAPI security dependencies wrapper bound to a JWT verifier provider."""

    def __init__(self, verifier_getter: Callable[[], JWTVerifier]) -> None:
        self._verifier_getter = verifier_getter

    async def get_optional_principal(
        self,
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    ) -> Principal | None:
        if credentials is None:
            return None
        if credentials.scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization scheme",
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            verifier = self._verifier_getter()
            principal = verifier.decode_and_verify(credentials.credentials)
            if verifier.revocation_checker is not None:
                is_revoked = await verifier.revocation_checker(principal.session_id)
                if is_revoked:
                    raise InvalidTokenError("Session has been revoked")
            return principal
        except (InvalidTokenError, ExpiredTokenError) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired access token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

    async def get_current_principal(
        self,
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    ) -> Principal:
        principal = await self.get_optional_principal(credentials)
        if principal is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return principal

    async def require_admin(
        self,
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    ) -> Principal:
        principal = await self.get_current_principal(credentials)
        if principal.role != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Administrator role required",
            )
        return principal


def create_auth_dependencies(
    verifier_getter: Callable[[], JWTVerifier]
) -> tuple[
    Callable[..., Awaitable[Principal | None]],
    Callable[..., Awaitable[Principal]],
    Callable[..., Awaitable[Principal]],
]:
    """Factory creating FastAPI dependencies bound to a verifier getter."""
    auth = JWTAuth(verifier_getter)
    return auth.get_optional_principal, auth.get_current_principal, auth.require_admin
