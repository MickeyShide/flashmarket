"""Public API routes for drops."""

from uuid import UUID

from fastapi import APIRouter, status

from drops.api.dependencies import DropServiceDep
from drops.application.schemas import DropResponse
from drops.domain.entities import DropStatus
from drops.domain.exceptions import DropNotFound

router = APIRouter(prefix="/api/v1/drops", tags=["drops"])


@router.get(
    "/active",
    response_model=list[DropResponse],
    status_code=status.HTTP_200_OK,
    summary="Get currently active drops",
)
async def list_active(service: DropServiceDep) -> list[DropResponse]:
    """Return all active flash-sale drops."""
    drops = await service.list_active()
    return [DropResponse.model_validate(drop) for drop in drops]


@router.get(
    "/upcoming",
    response_model=list[DropResponse],
    status_code=status.HTTP_200_OK,
    summary="Get upcoming scheduled drops",
)
async def list_upcoming(service: DropServiceDep) -> list[DropResponse]:
    """Return all scheduled upcoming drops."""
    drops = await service.list_upcoming()
    return [DropResponse.model_validate(drop) for drop in drops]


@router.get(
    "/id/{drop_id}",
    response_model=DropResponse,
    status_code=status.HTTP_200_OK,
    summary="Get public drop by ID",
)
async def get_drop_by_id(drop_id: UUID, service: DropServiceDep) -> DropResponse:
    drop = await service.get_by_id(drop_id)
    if drop.status in (DropStatus.DRAFT, DropStatus.CANCELLED):
        raise DropNotFound()
    return DropResponse.model_validate(drop)


@router.get(
    "/{slug}",
    response_model=DropResponse,
    status_code=status.HTTP_200_OK,
    summary="Get drop by slug",
)
async def get_drop(slug: str, service: DropServiceDep) -> DropResponse:
    """Return public drop details by slug. Hides DRAFT and CANCELLED drops."""
    drop = await service.get_by_slug(slug)
    if drop.status in (DropStatus.DRAFT, DropStatus.CANCELLED):
        raise DropNotFound()
    return DropResponse.model_validate(drop)
