"""Low-cardinality RabbitMQ reliability metrics shared by workers."""

import time
from threading import Lock

from prometheus_client import Counter, Gauge, start_http_server

_server_lock = Lock()
_server_started = False

PUBLISH_OUTCOMES = Counter(
    "flashmarket_rabbitmq_publish_total",
    "RabbitMQ confirmed publish attempts by outcome",
    ("outcome",),
)
CONSUMER_MOVES = Counter(
    "flashmarket_rabbitmq_consumer_move_total",
    "Failed consumer deliveries moved to retry or DLQ",
    ("destination",),
)
WORKER_LAST_SUCCESS = Gauge(
    "flashmarket_worker_last_success_unixtime",
    "Unix time of the last successful worker cycle",
    ("worker",),
    multiprocess_mode="mostrecent",
)
OUTBOX_OLDEST_PENDING = Gauge(
    "flashmarket_outbox_oldest_pending_seconds",
    "Age of the oldest unpublished outbox event",
    ("service",),
    multiprocess_mode="mostrecent",
)


def mark_worker_success(worker: str) -> None:
    WORKER_LAST_SUCCESS.labels(worker).set(time.time())


def start_worker_metrics_server(port: int = 9100) -> None:
    """Expose the current worker's single-process registry exactly once."""
    global _server_started
    with _server_lock:
        if _server_started:
            return
        start_http_server(port, addr="0.0.0.0")
        _server_started = True
