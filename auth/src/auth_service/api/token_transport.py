import hmac
import secrets

from fastapi import HTTPException, Request, Response, status

from auth_service.application.dto import IssuedTokens
from auth_service.config import get_settings
from auth_service.schemas import RefreshRequest, TokenPair


def clear_refresh_cookies(response: Response) -> None:
    """Remove the refresh and CSRF cookies."""
    settings = get_settings()
    response.delete_cookie(settings.refresh_cookie_name, path="/")
    response.delete_cookie(settings.csrf_cookie_name, path="/")


def deliver_tokens(response: Response, tokens: IssuedTokens) -> TokenPair:
    """Return tokens and set secure refresh cookies when enabled."""
    settings = get_settings()
    response_tokens = TokenPair(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        access_expires_in=tokens.access_expires_in,
    )
    if settings.refresh_token_transport == "body":
        return response_tokens

    csrf_token = secrets.token_urlsafe(32)
    max_age = settings.session_ttl_days * 24 * 60 * 60
    response.set_cookie(
        settings.refresh_cookie_name,
        tokens.refresh_token,
        max_age=max_age,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite=settings.refresh_cookie_samesite,
        path="/",
    )
    response.set_cookie(
        settings.csrf_cookie_name,
        csrf_token,
        max_age=max_age,
        httponly=False,
        secure=settings.refresh_cookie_secure,
        samesite=settings.refresh_cookie_samesite,
        path="/",
    )
    return response_tokens.model_copy(
        update={
            "refresh_token": None,
            "csrf_token": csrf_token,
        }
    )


def resolve_refresh_token(payload: RefreshRequest, request: Request) -> str:
    """Read the refresh token from the selected transport."""
    settings = get_settings()
    if settings.refresh_token_transport == "body":
        if payload.refresh_token is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="refresh_token is required",
            )
        return payload.refresh_token

    refresh_token = request.cookies.get(settings.refresh_cookie_name)
    csrf_cookie = request.cookies.get(settings.csrf_cookie_name)
    csrf_header = request.headers.get("x-csrf-token")
    if (
        refresh_token is None
        or csrf_cookie is None
        or csrf_header is None
        or not hmac.compare_digest(csrf_cookie, csrf_header)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Valid refresh cookie and CSRF token required",
        )
    return refresh_token
