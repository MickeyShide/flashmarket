import uuid

from fastapi import APIRouter, Query, Request

from auth_service.api.context import request_context
from auth_service.api.dependencies import AdminPrincipal, SessionStoreDep, Uow
from auth_service.application.admin import (
    ListUsers,
    UpdateUserRole,
    UpdateUserRoleCommand,
    UpdateUserStatus,
    UpdateUserStatusCommand,
)
from auth_service.application.contracts import UserSearch
from auth_service.models import UserRole
from auth_service.schemas import (
    AccountStatusUpdateRequest,
    RoleUpdateRequest,
    UserListResponse,
    UserResponse,
)

router = APIRouter(prefix="/admin/users", tags=["admin"])
update_user_role_use_case = UpdateUserRole()
update_user_status_use_case = UpdateUserStatus()
list_users_use_case = ListUsers()


@router.get("", response_model=UserListResponse)
async def list_users(
    _principal: AdminPrincipal,
    uow: Uow,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, min_length=1, max_length=120),
    role: UserRole | None = None,
    is_active: bool | None = None,
) -> UserListResponse:
    """Return a paginated user list for an administrator."""
    page = await list_users_use_case.execute(
        UserSearch(
            limit=limit,
            offset=offset,
            search=search,
            role=role,
            is_active=is_active,
        ),
        uow=uow,
    )
    return UserListResponse(
        items=[UserResponse.model_validate(user) for user in page.items],
        total=page.total,
        limit=limit,
        offset=offset,
    )


@router.patch("/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: uuid.UUID,
    payload: RoleUpdateRequest,
    request: Request,
    principal: AdminPrincipal,
    uow: Uow,
    session_store: SessionStoreDep,
) -> UserResponse:
    """Change a user role after administrator authorization."""
    user = await update_user_role_use_case.execute(
        UpdateUserRoleCommand(
            user_id=user_id,
            actor_user_id=principal.user_id,
            role=payload.role,
            context=request_context(request),
        ),
        uow=uow,
        session_store=session_store,
    )
    return UserResponse.model_validate(user)


@router.patch("/{user_id}/status", response_model=UserResponse)
async def update_user_status(
    user_id: uuid.UUID,
    payload: AccountStatusUpdateRequest,
    request: Request,
    principal: AdminPrincipal,
    uow: Uow,
    session_store: SessionStoreDep,
) -> UserResponse:
    """Enable or disable a user account."""
    user = await update_user_status_use_case.execute(
        UpdateUserStatusCommand(
            user_id=user_id,
            actor_user_id=principal.user_id,
            is_active=payload.is_active,
            context=request_context(request),
        ),
        uow=uow,
        session_store=session_store,
    )
    return UserResponse.model_validate(user)
