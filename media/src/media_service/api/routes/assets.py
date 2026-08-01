"""Public Media API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from media_service.api.dependencies import (
    AdminPrincipal,
    CurrentPrincipal,
    MediaServiceDep,
    OptionalPrincipal,
)
from media_service.application.schemas import (
    AssetListParams,
    AssetListResponse,
    AssetResponse,
    BindingRequest,
    CreateUploadRequest,
    CreateUploadResponse,
    PresignedUploadResponse,
)
from media_service.domain.entities import AssetStatus

router = APIRouter(prefix="/api/v1/media", tags=["media"])


@router.post(
    "/uploads",
    response_model=CreateUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a direct public-asset upload",
)
async def create_upload(
    request: CreateUploadRequest,
    principal: CurrentPrincipal,
    service: MediaServiceDep,
) -> CreateUploadResponse:
    session = await service.create_upload(principal, request)
    return CreateUploadResponse(
        asset=service.response(session.asset),
        upload=PresignedUploadResponse(
            url=session.post.url,
            fields=session.post.fields,
            expires_at=session.asset.upload_expires_at,
        ),
        complete_url=f"/api/v1/media/assets/{session.asset.id}/complete",
    )


@router.get("/assets/mine", response_model=AssetListResponse)
async def list_mine(
    params: Annotated[AssetListParams, Query()],
    principal: CurrentPrincipal,
    service: MediaServiceDep,
) -> AssetListResponse:
    page = await service.list_mine(
        principal,
        purpose=params.purpose,
        status=params.status,
        limit=params.limit,
        offset=params.offset,
    )
    return AssetListResponse(
        items=[service.response(item) for item in page.items],
        total=page.total,
        limit=params.limit,
        offset=params.offset,
    )


@router.get("/admin/assets", response_model=AssetListResponse)
async def list_admin_assets(
    principal: AdminPrincipal,
    service: MediaServiceDep,
    uploader_id: UUID | None = None,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    purpose: str | None = None,
    asset_status: AssetStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AssetListResponse:
    del principal
    page = await service.list_admin(
        uploader_id=uploader_id,
        entity_type=entity_type,
        entity_id=entity_id,
        purpose=purpose,
        status=asset_status,
        limit=limit,
        offset=offset,
    )
    return AssetListResponse(
        items=[service.response(item) for item in page.items],
        total=page.total,
        limit=limit,
        offset=offset,
    )


@router.post("/assets/{asset_id}/complete", response_model=AssetResponse)
async def complete_upload(
    asset_id: UUID,
    principal: CurrentPrincipal,
    service: MediaServiceDep,
) -> AssetResponse:
    return service.response(await service.complete(asset_id, principal))


@router.patch("/assets/{asset_id}/binding", response_model=AssetResponse)
async def bind_asset(
    asset_id: UUID,
    request: BindingRequest,
    principal: CurrentPrincipal,
    service: MediaServiceDep,
) -> AssetResponse:
    return service.response(await service.bind(asset_id, principal, request))


@router.delete(
    "/assets/{asset_id}", response_model=AssetResponse, status_code=status.HTTP_202_ACCEPTED
)
async def delete_asset(
    asset_id: UUID,
    principal: CurrentPrincipal,
    service: MediaServiceDep,
) -> AssetResponse:
    return service.response(await service.request_delete(asset_id, principal))


@router.get("/assets/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: UUID,
    principal: OptionalPrincipal,
    service: MediaServiceDep,
) -> AssetResponse:
    return service.response(await service.get_asset(asset_id, principal))


@router.get(
    "/entities/{entity_type}/{entity_id}/assets",
    response_model=AssetListResponse,
)
async def list_entity_assets(
    entity_type: str,
    entity_id: UUID,
    params: Annotated[AssetListParams, Query()],
    service: MediaServiceDep,
) -> AssetListResponse:
    page = await service.list_entity(
        entity_type=entity_type,
        entity_id=entity_id,
        purpose=params.purpose,
        limit=params.limit,
        offset=params.offset,
    )
    return AssetListResponse(
        items=[service.response(item) for item in page.items],
        total=page.total,
        limit=params.limit,
        offset=params.offset,
    )
