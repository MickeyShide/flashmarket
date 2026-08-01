"""Observability helpers for wishlist service: logging, request middleware, Prometheus metrics."""

import json
import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from datetime import UTC, datetime

from fastapi import Request, Response
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    multiprocess,
)

from wishlist.config import get_settings

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

HTTP_REQUESTS = Counter(
    "wishlist_http_requests_total",
    "Total HTTP requests",
    labelnames=("method", "route", "status"),
)
HTTP_DURATION = Histogram(
    "wishlist_http_request_duration_seconds",
    "HTTP request duration",
    labelnames=("method", "route"),
)
HTTP_IN_PROGRESS = Gauge(
    "wishlist_http_requests_in_progress",
    "HTTP requests currently in progress",
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
    if isinstance(value, list):
        return [_sanitize_value(key, item) for item in value]
    return value


class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            payload["exception"] = record.exc_text

        extra_fields: dict[str, object] = {}
        for key, val in record.__dict__.items():
            if key in {
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
            }:
                continue
            extra_fields[key] = _sanitize_value(key, val)

        if extra_fields:
            payload["extra"] = extra_fields

        return json.dumps(payload, separators=(",", ":"))


def setup_metrics() -> None:
    """Initialize structured logging."""
    settings = get_settings()
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    formatter = StructuredJsonFormatter()

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    handlers: list[logging.Handler] = []
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    handlers.append(stream_handler)

    if settings.log_file_path:
        from pathlib import Path

        log_path = Path(settings.log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    root_logger.handlers.clear()
    root_logger.handlers.extend(handlers)
    for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.handlers.extend(handlers)
        logger.propagate = False


def _extract_route_template(request: Request) -> str:
    for route in request.app.routes:
        match, _ = route.matches(request.scope)
        if match.name == "FULL":
            return getattr(route, "path", request.url.path)
    return request.url.path


async def request_observability_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Middleware for request tracking and metrics collection."""
    incoming_id = request.headers.get("x-request-id")
    if incoming_id and REQUEST_ID_PATTERN.match(incoming_id):
        request_id = incoming_id
    else:
        request_id = str(uuid.uuid4())

    token = request_id_var.set(request_id)
    request.state.request_id = request_id

    start_time = time.monotonic()
    HTTP_IN_PROGRESS.inc()
    route = _extract_route_template(request)

    try:
        response = await call_next(request)
        status_code = str(response.status_code)
    except Exception:
        status_code = "500"
        raise
    finally:
        duration = time.monotonic() - start_time
        HTTP_IN_PROGRESS.dec()
        HTTP_REQUESTS.labels(method=request.method, route=route, status=status_code).inc()
        HTTP_DURATION.labels(method=request.method, route=route).observe(duration)
        request_id_var.reset(token)

    response.headers["x-request-id"] = request_id
    return response


def metrics_endpoint() -> Response:
    """Prometheus metrics endpoint handler."""
    import os
    if "PROMETHEUS_MULTIPROC_DIR" in os.environ:
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
        content = generate_latest(registry)
    else:
        content = generate_latest()

    return Response(content=content, media_type="text/plain; version=0.0.4; charset=utf-8")
