"""Structured request logging and Media Prometheus metrics."""

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
from prometheus_client import Counter, Gauge, Histogram, generate_latest

from media_service.config import get_settings

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
HTTP_REQUESTS = Counter(
    "media_http_requests_total", "Total HTTP requests", ("method", "route", "status")
)
HTTP_DURATION = Histogram(
    "media_http_request_duration_seconds", "HTTP duration", ("method", "route")
)
HTTP_IN_PROGRESS = Gauge("media_http_requests_in_progress", "Requests in progress")
UPLOAD_SESSIONS = Counter("media_upload_sessions_total", "Created upload sessions", ("purpose",))
UPLOAD_COMPLETED = Counter("media_uploads_completed_total", "Completed uploads", ("purpose",))
UPLOAD_REJECTED = Counter("media_uploads_rejected_total", "Rejected uploads", ("reason",))
UPLOAD_BYTES = Counter("media_upload_bytes_total", "Published upload bytes", ("purpose",))
CLEANUP_FAILURES = Counter("media_cleanup_failures_total", "Cleanup failures")
S3_OPERATIONS = Counter("media_s3_operations_total", "S3 operations", ("operation", "result"))
S3_DURATION = Histogram(
    "media_s3_operation_duration_seconds", "S3 operation duration", ("operation",)
)
PENDING_ASSETS = Gauge("media_pending_assets", "Pending and verifying assets")
DELETION_QUEUE = Gauge("media_deletion_queue_size", "Assets awaiting physical deletion")

SENSITIVE = {"authorization", "secret", "secret_key", "access_key", "token", "fields", "policy"}
STANDARD_LOG_FIELDS = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__)


class StructuredJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        extras: dict[str, object] = {}
        for key, value in record.__dict__.items():
            if key.startswith("_") or key in STANDARD_LOG_FIELDS:
                continue
            extras[key] = "***MASKED***" if key.lower() in SENSITIVE else value
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        if extras:
            payload["extra"] = extras
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, separators=(",", ":"))


def setup_observability() -> None:
    settings = get_settings()
    root = logging.getLogger()
    root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    formatter = StructuredJsonFormatter()
    handlers: list[logging.Handler] = []

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    handlers.append(stream_handler)

    if settings.log_file_path:
        from pathlib import Path

        log_path = Path(settings.log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=10 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    root.handlers.clear()
    root.handlers.extend(handlers)
    for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.handlers.extend(handlers)
        logger.propagate = False


def _route(request: Request) -> str:
    for route in request.app.routes:
        match, _ = route.matches(request.scope)
        if match.name == "FULL":
            return str(getattr(route, "path", request.url.path))
    return request.url.path


async def request_observability_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    incoming = request.headers.get("x-request-id")
    request_id = (
        incoming if incoming and REQUEST_ID_PATTERN.fullmatch(incoming) else str(uuid.uuid4())
    )
    token = request_id_var.set(request_id)
    request.state.request_id = request_id
    started = time.monotonic()
    HTTP_IN_PROGRESS.inc()
    route = _route(request)
    status_code = "500"
    try:
        response = await call_next(request)
        status_code = str(response.status_code)
        response.headers["x-request-id"] = request_id
        return response
    finally:
        HTTP_IN_PROGRESS.dec()
        HTTP_REQUESTS.labels(request.method, route, status_code).inc()
        HTTP_DURATION.labels(request.method, route).observe(time.monotonic() - started)
        request_id_var.reset(token)


def metrics_endpoint() -> Response:
    return Response(generate_latest(), media_type="text/plain; version=0.0.4; charset=utf-8")
