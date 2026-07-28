import hashlib


def normalize_email(email: str) -> str:
    """Return the canonical email representation used for storage and lookup."""
    return email.strip().lower()


def fingerprint_identity(identity: str) -> str:
    """Return a stable non-plaintext fingerprint for rate limits and audit."""
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()
