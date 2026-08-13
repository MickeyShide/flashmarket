"""Validated transport settings independent from service configuration."""

from dataclasses import dataclass
from typing import Protocol, cast


class ReliabilitySettings(Protocol):
    rabbitmq_retry_delays_seconds: tuple[int, int, int]
    rabbitmq_publish_timeout_seconds: float
    rabbitmq_reconnect_initial_seconds: float
    rabbitmq_reconnect_max_seconds: float


@dataclass(frozen=True, slots=True)
class ReliabilityConfig:
    retry_delays_seconds: tuple[int, int, int] = (5, 30, 120)
    publish_timeout_seconds: float = 5.0
    reconnect_initial_seconds: float = 1.0
    reconnect_max_seconds: float = 30.0
    main_queue_max_length: int = 20_000
    main_queue_max_bytes: int = 128 * 1024 * 1024

    @classmethod
    def from_settings(cls, settings: ReliabilitySettings) -> ReliabilityConfig:
        """Build transport configuration from a service's validated settings."""
        return cls(
            retry_delays_seconds=cast(
                tuple[int, int, int], tuple(settings.rabbitmq_retry_delays_seconds)
            ),
            publish_timeout_seconds=settings.rabbitmq_publish_timeout_seconds,
            reconnect_initial_seconds=settings.rabbitmq_reconnect_initial_seconds,
            reconnect_max_seconds=settings.rabbitmq_reconnect_max_seconds,
        )

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
