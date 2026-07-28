class ApplicationError(Exception):
    code = "application_error"
    message = "The operation could not be completed"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)
        self.public_message = message or self.message


class EmailAlreadyExists(ApplicationError):
    code = "email_already_exists"
    message = "An account with this email already exists"


class InvalidCredentials(ApplicationError):
    code = "invalid_credentials"
    message = "Invalid email or password"


class AccountDisabled(ApplicationError):
    code = "account_disabled"
    message = "Account is disabled"


class InvalidRefreshToken(ApplicationError):
    code = "invalid_refresh_token"
    message = "Invalid or expired refresh token"


class RefreshTokenReuseDetected(InvalidRefreshToken):
    code = "refresh_token_reuse"


class SessionStoreUnavailable(ApplicationError):
    code = "session_store_unavailable"
    message = "Session store is unavailable"


class AccountUnavailable(ApplicationError):
    code = "account_unavailable"
    message = "Account is unavailable"


class CurrentPasswordIncorrect(ApplicationError):
    code = "current_password_incorrect"
    message = "Current password is incorrect"


class PasswordUnchanged(ApplicationError):
    code = "password_unchanged"
    message = "New password must be different"


class SessionNotFound(ApplicationError):
    code = "session_not_found"
    message = "Session not found"


class UserNotFound(ApplicationError):
    code = "user_not_found"
    message = "User not found"


class OwnRoleChangeForbidden(ApplicationError):
    code = "own_role_change_forbidden"
    message = "Administrators cannot change their own role"


class OwnAccountDisableForbidden(ApplicationError):
    code = "own_account_disable_forbidden"
    message = "Administrators cannot disable their own account"
