"""Prometheus endpoint."""

from fastapi import APIRouter, Response

from media_service.observability import metrics_endpoint

router = APIRouter(tags=["metrics"])


@router.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return metrics_endpoint()
