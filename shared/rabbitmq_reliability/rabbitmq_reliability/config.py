"""Validated transport settings independent from service configuration."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReliabilityConfig:
    retry_delays_seconds: tuple[int, int, int] = (5, 30, 120)
    publish_timeout_seconds: float = 5.0
    reconnect_initial_seconds: float = 1.0
    reconnect_max_seconds: float = 30.0
    main_queue_max_length: int = 20_000
    main_queue_max_bytes: int = 128 * 1024 * 1024

    def __post_init__(self) -> None:
        if len(self.retry_delays_seconds) != 3:
            raise ValueError("exactly three retry delays are required")
        if any(delay <= 0 for delay in self.retry_delays_seconds):
            raise ValueError("retry delays must be positive")
        if tuple(sorted(self.retry_delays_seconds)) != self.retry_delays_seconds:
            raise ValueError("retry delays must be ordered")
        if self.publish_timeout_seconds <= 0:
            raise ValueError("publish timeout must be positive")
        if not 0 < self.reconnect_initial_seconds <= self.reconnect_max_seconds:
            raise ValueError("invalid reconnect delay bounds")
        if min(self.main_queue_max_length, self.main_queue_max_bytes) <= 0:
            raise ValueError("queue bounds must be positive")
