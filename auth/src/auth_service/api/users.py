from fastapi import APIRouter, Request, Response

from auth_service.api.context import request_context
from auth_service.api.dependencies import CurrentPrincipal, SessionStoreDep, Uow
from auth_service.api.token_transport import clear_refresh_cookies
from auth_service.application.contracts import AuthenticatedIdentity
from auth_service.application.users import (
    ChangePassword,
    ChangePasswordCommand,
    GetProfile,
    UpdateProfile,
    UpdateProfileCommand,
)
from auth_service.schemas import (
    MessageResponse,
    PasswordChangeRequest,
    ProfileUpdateRequest,
    UserResponse,
)

router = APIRouter(prefix="/users", tags=["users"])
update_profile_use_case = UpdateProfile()
change_password_use_case = ChangePassword()
get_profile_use_case = GetProfile()


@router.get("/me", response_model=UserResponse)
async def get_profile(
    principal: CurrentPrincipal,
    uow: Uow,
) -> UserResponse:
    """Return the current user’s public profile."""
    user = await get_profile_use_case.execute(principal.user_id, uow=uow)
    return UserResponse.model_validate(user)


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    payload: ProfileUpdateRequest,
    request: Request,
    principal: CurrentPrincipal,
    uow: Uow,
) -> UserResponse:
    """Update the current user’s profile fields."""
    user = await update_profile_use_case.execute(
        UpdateProfileCommand(
            identity=AuthenticatedIdentity(
                user_id=principal.user_id,
                session_id=principal.session_id,
            ),
            context=request_context(request),
            update_full_name="full_name" in payload.model_fields_set,
            full_name=payload.full_name,
        ),
        uow=uow,
    )
    return UserResponse.model_validate(user)


@router.post("/me/password", response_model=MessageResponse)
async def change_password(
    payload: PasswordChangeRequest,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    uow: Uow,
    session_store: SessionStoreDep,
) -> MessageResponse:
    """Change the current password and revoke old sessions."""
    await change_password_use_case.execute(
        ChangePasswordCommand(
            identity=AuthenticatedIdentity(
                user_id=principal.user_id,
                session_id=principal.session_id,
            ),
            context=request_context(request),
            current_password=payload.current_password,
            new_password=payload.new_password,
        ),
        uow=uow,
        session_store=session_store,
    )
    clear_refresh_cookies(response)
    return MessageResponse(message="Password changed; sign in again")
