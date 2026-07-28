from fastapi import APIRouter, Request, Response, status

from auth_service.api.context import request_context, request_metadata
from auth_service.api.dependencies import CurrentPrincipal, SessionStoreDep, Uow
from auth_service.api.token_transport import (
    clear_refresh_cookies,
    deliver_tokens,
    resolve_refresh_token,
)
from auth_service.application.auth import (
    IntrospectAccessToken,
    LoginCommand,
    LoginUser,
    LogoutCommand,
    LogoutUser,
    RefreshAccess,
    RefreshCommand,
    RegisterCommand,
    RegisterUser,
)
from auth_service.application.contracts import AuthenticatedIdentity
from auth_service.application.errors import InvalidRefreshToken
from auth_service.cache import Cache
from auth_service.config import get_settings
from auth_service.rate_limit import enforce_rate_limit
from auth_service.schemas import (
    AuthResponse,
    IntrospectionRequest,
    IntrospectionResponse,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    TokenRefreshResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])

register_user = RegisterUser()
login_user = LoginUser()
refresh_access = RefreshAccess()
introspect_access_token = IntrospectAccessToken()
logout_user = LogoutUser()


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    uow: Uow,
    cache: Cache,
    session_store: SessionStoreDep,
) -> AuthResponse:
    settings = get_settings()
    _, ip_address = request_metadata(request)
    await enforce_rate_limit(
        cache,
        scope="register",
        identity=ip_address or "unknown",
        limit=settings.register_rate_limit,
        window_seconds=settings.register_rate_window_seconds,
    )
    result = await register_user.execute(
        RegisterCommand(
            email=str(payload.email),
            password=payload.password,
            full_name=payload.full_name,
            context=request_context(request),
        ),
        uow=uow,
        session_store=session_store,
    )
    return AuthResponse(
        user=result.user,
        tokens=deliver_tokens(response, result.tokens),
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    uow: Uow,
    cache: Cache,
    session_store: SessionStoreDep,
) -> AuthResponse:
    settings = get_settings()
    _, ip_address = request_metadata(request)
    email = str(payload.email).lower()
    await enforce_rate_limit(
        cache,
        scope="login-ip",
        identity=ip_address or "unknown",
        limit=settings.login_rate_limit,
        window_seconds=settings.login_rate_window_seconds,
    )
    await enforce_rate_limit(
        cache,
        scope="login-account",
        identity=email,
        limit=settings.login_rate_limit,
        window_seconds=settings.login_rate_window_seconds,
    )
    result = await login_user.execute(
        LoginCommand(
            email=email,
            password=payload.password,
            context=request_context(request),
        ),
        uow=uow,
        session_store=session_store,
    )
    return AuthResponse(
        user=result.user,
        tokens=deliver_tokens(response, result.tokens),
    )


@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh(
    payload: RefreshRequest,
    request: Request,
    response: Response,
    uow: Uow,
    cache: Cache,
    session_store: SessionStoreDep,
) -> TokenRefreshResponse:
    settings = get_settings()
    _, ip_address = request_metadata(request)
    await enforce_rate_limit(
        cache,
        scope="refresh",
        identity=ip_address or "unknown",
        limit=settings.refresh_rate_limit,
        window_seconds=settings.refresh_rate_window_seconds,
    )
    raw_refresh_token = resolve_refresh_token(payload, request)
    try:
        result = await refresh_access.execute(
            RefreshCommand(
                refresh_token=raw_refresh_token,
                context=request_context(request),
            ),
            uow=uow,
            session_store=session_store,
        )
    except InvalidRefreshToken:
        clear_refresh_cookies(response)
        raise
    return TokenRefreshResponse(tokens=deliver_tokens(response, result.tokens))


@router.post("/introspect", response_model=IntrospectionResponse)
async def introspect(
    payload: IntrospectionRequest,
    request: Request,
    cache: Cache,
    session_store: SessionStoreDep,
) -> IntrospectionResponse:
    settings = get_settings()
    _, ip_address = request_metadata(request)
    await enforce_rate_limit(
        cache,
        scope="introspection",
        identity=ip_address or "unknown",
        limit=settings.introspection_rate_limit,
        window_seconds=settings.introspection_rate_window_seconds,
    )
    claims = await introspect_access_token.execute(
        payload.token,
        session_store=session_store,
    )
    if claims is None:
        return IntrospectionResponse(active=False)
    return IntrospectionResponse(
        active=True,
        sub=claims.user_id,
        sid=claims.session_id,
        role=claims.role,
        exp=claims.expires_at,
        iss=settings.jwt_issuer,
        aud=settings.jwt_audience,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    uow: Uow,
    session_store: SessionStoreDep,
) -> MessageResponse:
    await logout_user.execute(
        LogoutCommand(
            identity=AuthenticatedIdentity(
                user_id=principal.user_id,
                session_id=principal.session_id,
            ),
            context=request_context(request),
        ),
        uow=uow,
        session_store=session_store,
    )
    clear_refresh_cookies(response)
    return MessageResponse(message="Session closed")
