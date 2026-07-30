"""Prometheus metrics endpoint."""

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST

from inventory.observability import generate_metrics

router = APIRouter(tags=["metrics"])


@router.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    """Expose Prometheus metrics."""
    return Response(
        content=generate_metrics(),
        media_type=CONTENT_TYPE_LATEST,
    )
