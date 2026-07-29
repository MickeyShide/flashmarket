"""Internal/admin endpoints for the inventory service."""

from fastapi import APIRouter

from inventory.api.dependencies import InventoryServiceDep

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post(
    "/expire",
    response_model=dict[str, int],
    summary="Expire stale reservations",
)
async def expire_reservations(
    service: InventoryServiceDep,
    batch_size: int = 100,
) -> dict[str, int]:
    """Release expired reservations. Usually invoked by a periodic worker."""
    expired_count = await service.expire_reservations(batch_size=batch_size)
    return {"expired": expired_count}
