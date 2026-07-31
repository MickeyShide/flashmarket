"""Prometheus metrics endpoint for the wishlist service."""

from fastapi import APIRouter, Response

from wishlist.observability import metrics_endpoint

router = APIRouter(tags=["metrics"])


@router.get("/metrics", include_in_schema=False)
async def get_metrics() -> Response:
    """Expose Prometheus metrics for scraping."""
    return metrics_endpoint()
