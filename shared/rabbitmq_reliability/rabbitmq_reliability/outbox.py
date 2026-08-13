"""Pure outbox retry scheduling helpers."""

import random

from rabbitmq_reliability.delivery import sanitize_error


def retry_backoff_seconds(
    attempts: int,
    *,
    maximum: float = 300.0,
    random_value: float | None = None,
) -> float:
    ceiling = min(maximum, float(2 ** min(max(1, attempts), 9)))
    factor = random.random() if random_value is None else random_value
    return max(0.1, ceiling * max(0.0, min(1.0, factor)))


__all__ = ["retry_backoff_seconds", "sanitize_error"]
