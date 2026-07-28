import uuid

from fastapi import APIRouter, Query

from auth_service.api.dependencies import AdminPrincipal, Uow
from auth_service.application.admin import ListAuditEvents
from auth_service.application.contracts import AuditEventSearch
from auth_service.schemas import AuditEventListResponse, AuditEventResponse

router = APIRouter(prefix="/admin/audit-events", tags=["admin"])
list_audit_events_use_case = ListAuditEvents()


@router.get("", response_model=AuditEventListResponse)
async def list_audit_events(
    _principal: AdminPrincipal,
    uow: Uow,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    event_type: str | None = Query(default=None, min_length=1, max_length=64),
    user_id: uuid.UUID | None = None,
) -> AuditEventListResponse:
    page = await list_audit_events_use_case.execute(
        AuditEventSearch(
            limit=limit,
            offset=offset,
            event_type=event_type,
            user_id=user_id,
        ),
        uow=uow,
    )
    return AuditEventListResponse(
        items=[AuditEventResponse.model_validate(event) for event in page.items],
        total=page.total,
        limit=limit,
        offset=offset,
    )
