import json
import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from fastapi import Request, Response
from prometheus_client import Counter, Gauge, Histogram

from auth_service.config import get_settings

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

HTTP_REQUESTS = Counter(
    "auth_http_requests_total",
    "Total HTTP requests",
    labelnames=("method", "route", "status"),
)
HTTP_DURATION = Histogram(
    "auth_http_request_duration_seconds",
    "HTTP request duration",
    labelnames=("method", "route"),
)
HTTP_IN_PROGRESS = Gauge(
    "auth_http_requests_in_progress",
    "HTTP requests currently in progress",
)
RATE_LIMIT_REJECTIONS = Counter(
    "auth_rate_limit_rejections_total",
    "Requests rejected by the distributed rate limiter",
    labelnames=("scope",),
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
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
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("auth.http")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    return logger


http_logger = configure_logging()


async def request_observability_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    supplied_request_id = request.headers.get("x-request-id", "")
    request_id = (
        supplied_request_id
        if REQUEST_ID_PATTERN.fullmatch(supplied_request_id)
        else str(uuid.uuid7())
    )
    request.state.request_id = request_id
    started_at = time.perf_counter()
    status_code = 500
    HTTP_IN_PROGRESS.inc()
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        if get_settings().environment == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
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
