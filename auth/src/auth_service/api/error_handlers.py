from fastapi import Request, status
from fastapi.responses import JSONResponse

from auth_service.application.errors import (
    AccountDisabled,
    AccountUnavailable,
    ApplicationError,
    CurrentPasswordIncorrect,
    EmailAlreadyExists,
    InvalidCredentials,
    InvalidRefreshToken,
    OwnAccountDisableForbidden,
    OwnRoleChangeForbidden,
    PasswordUnchanged,
    SessionNotFound,
    SessionStoreUnavailable,
    UserNotFound,
)

ERROR_STATUS: dict[type[ApplicationError], int] = {
    EmailAlreadyExists: status.HTTP_409_CONFLICT,
    InvalidCredentials: status.HTTP_401_UNAUTHORIZED,
    AccountDisabled: status.HTTP_403_FORBIDDEN,
    AccountUnavailable: status.HTTP_401_UNAUTHORIZED,
    InvalidRefreshToken: status.HTTP_401_UNAUTHORIZED,
    SessionStoreUnavailable: status.HTTP_503_SERVICE_UNAVAILABLE,
    CurrentPasswordIncorrect: status.HTTP_400_BAD_REQUEST,
    PasswordUnchanged: status.HTTP_409_CONFLICT,
    SessionNotFound: status.HTTP_404_NOT_FOUND,
    UserNotFound: status.HTTP_404_NOT_FOUND,
    OwnRoleChangeForbidden: status.HTTP_409_CONFLICT,
    OwnAccountDisableForbidden: status.HTTP_409_CONFLICT,
}


async def application_error_handler(
    request: Request,
    exc: ApplicationError,
) -> JSONResponse:
    status_code = next(
        (
            error_status
            for error_type, error_status in ERROR_STATUS.items()
            if isinstance(exc, error_type)
        ),
        status.HTTP_400_BAD_REQUEST,
    )
    headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None
    return JSONResponse(
        status_code=status_code,
        headers=headers,
        content={
            "error": {
                "code": exc.code,
                "message": exc.public_message,
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )
