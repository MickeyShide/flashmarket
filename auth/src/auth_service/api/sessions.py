import uuid

from fastapi import APIRouter, Request

from auth_service.api.context import request_context
from auth_service.api.dependencies import CurrentPrincipal, SessionStoreDep, Uow
from auth_service.application.contracts import AuthenticatedIdentity
from auth_service.application.sessions import (
    ListSessions,
    RevokeAllSessions,
    RevokeAllSessionsCommand,
    RevokeSession,
    RevokeSessionCommand,
)
from auth_service.models import LoginSession
from auth_service.schemas import MessageResponse, SessionResponse
from auth_service.time import as_utc, utc_now

router = APIRouter(prefix="/sessions", tags=["sessions"])
revoke_session_use_case = RevokeSession()
revoke_all_sessions_use_case = RevokeAllSessions()
list_sessions_use_case = ListSessions()


def serialize_session(
    login_session: LoginSession,
    *,
    current_session_id: uuid.UUID,
) -> SessionResponse:
    """Convert a login session to its API representation."""
    active = login_session.revoked_at is None and as_utc(login_session.expires_at) > utc_now()
    return SessionResponse(
        id=login_session.id,
        current=login_session.id == current_session_id,
        user_agent=login_session.user_agent,
        ip_address=login_session.ip_address,
        created_at=login_session.created_at,
        last_seen_at=login_session.last_seen_at,
        expires_at=login_session.expires_at,
        revoked_at=login_session.revoked_at,
        active=active,
    )


@router.get("", response_model=list[SessionResponse])
async def list_sessions(
    principal: CurrentPrincipal,
    uow: Uow,
) -> list[SessionResponse]:
    """Return the current user’s sessions with their active state."""
    sessions = await list_sessions_use_case.execute(principal.user_id, uow=uow)
    return [serialize_session(item, current_session_id=principal.session_id) for item in sessions]


@router.delete("/{session_id}", response_model=MessageResponse)
async def close_session(
    session_id: uuid.UUID,
    request: Request,
    principal: CurrentPrincipal,
    uow: Uow,
    session_store: SessionStoreDep,
) -> MessageResponse:
    """Revoke one of the current user’s sessions."""
    await revoke_session_use_case.execute(
        RevokeSessionCommand(
            identity=AuthenticatedIdentity(
                user_id=principal.user_id,
                session_id=principal.session_id,
            ),
            context=request_context(request),
            session_id=session_id,
        ),
        uow=uow,
        session_store=session_store,
    )
    return MessageResponse(message="Session closed")


@router.delete("", response_model=MessageResponse)
async def close_all_sessions(
    request: Request,
    principal: CurrentPrincipal,
    uow: Uow,
    session_store: SessionStoreDep,
) -> MessageResponse:
    """Revoke every session, including the current one."""
    session_count = await revoke_all_sessions_use_case.execute(
        RevokeAllSessionsCommand(
            identity=AuthenticatedIdentity(
                user_id=principal.user_id,
                session_id=principal.session_id,
            ),
            context=request_context(request),
        ),
        uow=uow,
        session_store=session_store,
    )
    return MessageResponse(message=f"Closed {session_count} session(s)")
