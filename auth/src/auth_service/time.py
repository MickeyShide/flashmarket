from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return the current time in UTC."""
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    """Convert a datetime to UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
