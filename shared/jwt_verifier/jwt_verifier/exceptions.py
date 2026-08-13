class JWTVerificationError(Exception):
    """Base exception for JWT verification errors."""


class InvalidTokenError(JWTVerificationError):
    """Token signature or claims are invalid."""


class ExpiredTokenError(JWTVerificationError):
    """Token has expired."""


class KeyStoreError(JWTVerificationError):
    """Public key store is missing, empty, or invalid."""
