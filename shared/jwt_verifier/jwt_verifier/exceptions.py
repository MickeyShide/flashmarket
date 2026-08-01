class JWTVerificationError(Exception):
    """Base exception for JWT verification errors."""

    pass


class InvalidTokenError(JWTVerificationError):
    """Token signature or claims are invalid."""

    pass


class ExpiredTokenError(JWTVerificationError):
    """Token has expired."""

    pass


class KeyStoreError(JWTVerificationError):
    """Public key store is missing, empty, or invalid."""

    pass
