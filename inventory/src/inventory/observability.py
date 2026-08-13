"""Observability helpers: logging, request middleware, Prometheus metrics."""

import json
import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler

from fastapi import Request, Response
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    multiprocess,
)

from inventory.config import get_settings

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

HTTP_REQUESTS = Counter(
    "inventory_http_requests_total",
    "Total HTTP requests",
    labelnames=("method", "route", "status"),
)
HTTP_DURATION = Histogram(
    "inventory_http_request_duration_seconds",
    "HTTP request duration",
    labelnames=("method", "route"),
)
HTTP_IN_PROGRESS = Gauge(
    "inventory_http_requests_in_progress",
    "HTTP requests currently in progress",
)
STOCK_CACHE_OPERATIONS = Counter(
    "inventory_stock_cache_operations_total",
    "Inventory stock cache operations",
    labelnames=("operation", "result"),
)

SENSITIVE_KEYS = {
    "password",
    "secret",
    "secret_key",
    "access_key",
    "authorization",
    "token",
    "access_token",
    "refresh_token",
    "cookie",
}


def _sanitize_value(key: str, value: object) -> object:
    if isinstance(key, str) and key.lower() in SENSITIVE_KEYS:
        return "***MASKED***"
    if isinstance(value, dict):
        return {k: _sanitize_value(k, v) for k, v in value.items()}
    return value


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as a JSON line."""
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in (
            "request_id",
            "method",
            "route",
            "status_code",
            "duration_ms",
        ):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value

        standard_attrs = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "taskName",
        }
        for key, value in record.__dict__.items():
            if key not in standard_attrs and not key.startswith("_") and key not in payload:
                payload[key] = _sanitize_value(key, value)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> logging.Logger:
    """Configure structured application logging."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    formatter = JsonFormatter()
    handlers: list[logging.Handler] = []

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    handlers.append(stream_handler)

    log_file_path = get_settings().log_file_path
    if log_file_path:
        from pathlib import Path

        log_path = Path(log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=10 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    root_logger.handlers.clear()
    for handler in handlers:
        root_logger.addHandler(handler)

    for logger_name in (
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
    ):
        lg = logging.getLogger(logger_name)
        lg.handlers.clear()
        for handler in handlers:
            lg.addHandler(handler)
        lg.propagate = False

    logger = logging.getLogger("inventory.http")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        logger.addHandler(stream_handler)
    return logger


http_logger = configure_logging()


def setup_metrics() -> None:
    """Prepare shared Prometheus multiprocess storage when configured."""
    from pathlib import Path

    directory = get_settings().prometheus_multiproc_dir
    if directory:
        Path(directory).mkdir(parents=True, exist_ok=True)


def generate_metrics() -> bytes:
    """Collect API counters from the shared multiprocess registry."""
    directory = get_settings().prometheus_multiproc_dir
    if not directory:
        return generate_latest()

    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)  # type: ignore[no-untyped-call]
    return generate_latest(registry)


async def request_observability_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Record request timing, status, and correlation ID."""
    supplied_request_id = request.headers.get("x-request-id", "")
    request_id = (
        supplied_request_id
        if REQUEST_ID_PATTERN.fullmatch(supplied_request_id)
        else str(uuid.uuid4())
    )
    request.state.request_id = request_id
    token = request_id_var.set(request_id)
    started_at = time.perf_counter()
    status_code = 500
    HTTP_IN_PROGRESS.inc()
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        route = request.scope.get("route")
        route_path = getattr(route, "path", "unmatched")
        duration = time.perf_counter() - started_at
        HTTP_REQUESTS.labels(
            method=request.method,
            route=route_path,
            status=str(status_code),
        ).inc()
        HTTP_DURATION.labels(
            method=request.method,
            route=route_path,
        ).observe(duration)
        HTTP_IN_PROGRESS.dec()
        request_id_var.reset(token)
        http_logger.info(
            "HTTP request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "route": route_path,
                "status_code": status_code,
                "duration_ms": round(duration * 1000, 2),
            },
        )
