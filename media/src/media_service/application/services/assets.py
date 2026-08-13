"""Media asset lifecycle application service."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from jwt_verifier import Principal
from sqlalchemy.ext.asyncio import AsyncSession

from media_service.application.contracts import ObjectStorage
from media_service.application.schemas import (
    AssetResponse,
    BindingRequest,
    CreateUploadRequest,
)
from media_service.application.validation_gate import ValidationGate
from media_service.config import Settings
from media_service.domain.entities import AssetStatus, PresignedPost, Visibility
from media_service.domain.exceptions import (
    AssetAccessDenied,
    AssetNotFound,
    FileTooLarge,
    InvalidAssetState,
    MediaError,
    MediaQuotaExceeded,
    StorageObjectNotFound,
    StorageUnavailable,
    UnsupportedContentType,
    UploadExpired,
    UploadValidationFailed,
)
from media_service.domain.policies import (
    IMAGE_TYPES,
    authorize_upload,
    get_policy,
    sanitize_filename,
    validate_binding,
    validate_content,
    validate_declaration,
)
from media_service.infrastructure.models import MediaAssetModel
from media_service.infrastructure.repositories import AssetPage, MediaAssetRepository
from media_service.observability import (
    DELETION_QUEUE,
    PENDING_ASSETS,
    UPLOAD_BYTES,
    UPLOAD_COMPLETED,
    UPLOAD_REJECTED,
    UPLOAD_SESSIONS,
)


@dataclass(frozen=True, slots=True)
class UploadSession:
    """New asset plus its direct-upload contract."""

    asset: MediaAssetModel
    post: PresignedPost


class MediaAssetService:
    """Coordinate persistence, policy, and object storage."""

    def __init__(
        self,
        session: AsyncSession,
        repository: MediaAssetRepository,
        storage: ObjectStorage,
        settings: Settings,
        validation_gate: ValidationGate,
    ) -> None:
        self._session = session
        self._repository = repository
        self._storage = storage
        self._settings = settings
        self._validation_gate = validation_gate

    def public_url(self, asset: MediaAssetModel) -> str:
        """Build an immutable browser URL without leaking the internal endpoint."""
        encoded_key = quote(asset.object_key, safe="/")
        return f"{self._settings.public_base_url.rstrip('/')}/{encoded_key}"

    def response(self, asset: MediaAssetModel) -> AssetResponse:
        """Map trusted persistence metadata to an API representation."""
        ready = asset.status == AssetStatus.READY
        return AssetResponse(
            id=asset.id,
            uploader_id=asset.uploader_id,
            purpose=asset.purpose,
            entity_type=asset.entity_type,
            entity_id=asset.entity_id,
            status=asset.status,
            visibility=asset.visibility,
            original_filename=asset.original_filename,
            content_type=asset.detected_content_type or asset.declared_content_type,
            size=asset.actual_size or asset.expected_size,
            sha256=asset.sha256,
            width=asset.width,
            height=asset.height,
            public_url=self.public_url(asset) if ready else None,
            upload_expires_at=asset.upload_expires_at,
            uploaded_at=asset.uploaded_at,
            created_at=asset.created_at,
            updated_at=asset.updated_at,
        )

    async def create_upload(
        self, principal: Principal, request: CreateUploadRequest
    ) -> UploadSession:
        """Persist a constrained upload session and generate a presigned POST."""
        policy = get_policy(request.purpose)
        authorize_upload(
            policy=policy,
            user_id=principal.user_id,
            role=principal.role,
            entity_type=request.entity_type,
            entity_id=request.entity_id,
        )
        validate_declaration(policy, request.content_type, request.size)
        filename = sanitize_filename(request.filename)

        if principal.role != "ADMIN":
            usage = await self._repository.user_usage(principal.user_id)
            if usage.pending >= self._settings.max_pending_per_user:
                raise MediaQuotaExceeded("Too many active upload sessions")
            if usage.ready >= self._settings.max_user_assets:
                raise MediaQuotaExceeded("Media asset count quota exceeded")
            if usage.ready_bytes + request.size > self._settings.max_user_bytes:
                raise MediaQuotaExceeded("Media storage quota exceeded")

        now = datetime.now(UTC)
        asset_id = uuid.uuid7()
        key = f"{request.purpose}/{now:%Y/%m}/{asset_id}/{filename}"
        asset = MediaAssetModel(
            id=asset_id,
            uploader_id=principal.user_id,
            purpose=request.purpose,
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            status=AssetStatus.PENDING,
            visibility=Visibility.PUBLIC,
            bucket=self._settings.s3_bucket,
            object_key=key,
            original_filename=filename,
            declared_content_type=request.content_type,
            expected_size=request.size,
            upload_expires_at=now + timedelta(seconds=self._settings.upload_ttl_seconds),
        )
        await self._repository.add(asset)
        post = await self._storage.create_presigned_post(
            key=key,
            content_type=request.content_type,
            size=request.size,
            asset_id=str(asset.id),
            expires_in=self._settings.upload_ttl_seconds,
            inline=request.content_type in IMAGE_TYPES,
        )
        await self._session.commit()
        UPLOAD_SESSIONS.labels(asset.purpose).inc()
        await self._refresh_queue_metrics()
        return UploadSession(asset=asset, post=post)

    async def complete(self, asset_id: uuid.UUID, principal: Principal) -> MediaAssetModel:
        """Verify an uploaded object and atomically publish its metadata."""
        asset = await self._get_owned(asset_id, principal, for_update=True)
        if asset.status == AssetStatus.READY:
            return asset
        if asset.status not in {AssetStatus.PENDING, AssetStatus.VERIFYING}:
            raise InvalidAssetState()
        expires_at = asset.upload_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at <= datetime.now(UTC):
            asset.status = AssetStatus.EXPIRED
            asset.failure_code = "upload_expired"
            await self._session.commit()
            await self._delete_best_effort(asset.object_key)
            raise UploadExpired()

        asset.status = AssetStatus.VERIFYING
        await self._session.flush()
        try:
            stored = await self._storage.head_object(asset.object_key)
            if stored.size != asset.expected_size:
                raise UploadValidationFailed("Stored object size does not match the upload session")
            if stored.content_type != asset.declared_content_type:
                raise UnsupportedContentType()
            if stored.metadata.get("asset-id") != str(asset.id):
                raise UploadValidationFailed(
                    "Stored object metadata does not match the upload session"
                )
            async def read_and_validate():  # type: ignore[no-untyped-def]
                content = await self._storage.read_object(
                    asset.object_key, asset.expected_size
                )
                if len(content) != asset.expected_size:
                    raise UploadValidationFailed(
                        "Stored object size does not match the upload session"
                    )
                validated = validate_content(
                    content,
                    asset.declared_content_type,
                    self._settings.max_image_pixels,
                )
                return content, validated

            content, validated = await self._validation_gate.run(read_and_validate)
        except StorageObjectNotFound:
            asset.status = AssetStatus.PENDING
            await self._session.commit()
            raise
        except StorageUnavailable:
            asset.status = AssetStatus.PENDING
            await self._session.commit()
            raise
        except (UploadValidationFailed, UnsupportedContentType, FileTooLarge) as exc:
            asset.status = AssetStatus.REJECTED
            asset.failure_code = exc.code
            await self._session.commit()
            await self._delete_best_effort(asset.object_key)
            UPLOAD_REJECTED.labels(exc.code).inc()
            await self._refresh_queue_metrics()
            raise

        asset.detected_content_type = validated.content_type
        asset.actual_size = len(content)
        asset.sha256 = validated.sha256
        asset.width = validated.width
        asset.height = validated.height
        asset.status = AssetStatus.READY
        asset.uploaded_at = datetime.now(UTC)
        asset.failure_code = None
        await self._session.commit()
        UPLOAD_COMPLETED.labels(asset.purpose).inc()
        UPLOAD_BYTES.labels(asset.purpose).inc(len(content))
        await self._refresh_queue_metrics()
        return asset

    async def get_asset(self, asset_id: uuid.UUID, principal: Principal | None) -> MediaAssetModel:
        """Return a ready public asset or authorize non-ready metadata."""
        asset = await self._repository.get(asset_id)
        if asset is None or asset.status in {AssetStatus.DELETED, AssetStatus.EXPIRED}:
            raise AssetNotFound()
        if asset.status != AssetStatus.READY:
            if principal is None or not self._can_manage(asset, principal):
                raise AssetNotFound()
        return asset

    async def list_mine(
        self,
        principal: Principal,
        *,
        purpose: str | None,
        status: AssetStatus | None,
        limit: int,
        offset: int,
    ) -> AssetPage:
        """List the current user's upload history."""
        return await self._repository.list_assets(
            uploader_id=principal.user_id,
            purpose=purpose,
            status=status,
            limit=limit,
            offset=offset,
        )

    async def list_entity(
        self,
        *,
        entity_type: str,
        entity_id: uuid.UUID,
        purpose: str | None,
        limit: int,
        offset: int,
    ) -> AssetPage:
        """List ready public assets bound to one domain entity."""
        if not entity_type or len(entity_type) > 64:
            raise AssetNotFound()
        return await self._repository.list_assets(
            entity_type=entity_type,
            entity_id=entity_id,
            purpose=purpose,
            status=AssetStatus.READY,
            limit=limit,
            offset=offset,
        )

    async def list_admin(
        self,
        *,
        uploader_id: uuid.UUID | None,
        entity_type: str | None,
        entity_id: uuid.UUID | None,
        purpose: str | None,
        status: AssetStatus | None,
        limit: int,
        offset: int,
    ) -> AssetPage:
        """List assets with administrator filters."""
        return await self._repository.list_assets(
            uploader_id=uploader_id,
            entity_type=entity_type,
            entity_id=entity_id,
            purpose=purpose,
            status=status,
            limit=limit,
            offset=offset,
        )

    async def bind(
        self,
        asset_id: uuid.UUID,
        principal: Principal,
        request: BindingRequest,
    ) -> MediaAssetModel:
        """Attach an existing asset to a domain entity under its purpose policy."""
        asset = await self._get_owned(asset_id, principal, for_update=True)
        if asset.status not in {AssetStatus.PENDING, AssetStatus.READY}:
            raise InvalidAssetState()
        policy = get_policy(asset.purpose)
        if policy.admin_only and principal.role != "ADMIN":
            raise AssetAccessDenied()
        validate_binding(policy, request.entity_type, request.entity_id)
        if (
            policy.owner_entity
            and principal.role != "ADMIN"
            and request.entity_id != principal.user_id
        ):
            raise AssetAccessDenied()
        asset.entity_type = request.entity_type
        asset.entity_id = request.entity_id
        await self._session.commit()
        return asset

    async def request_delete(self, asset_id: uuid.UUID, principal: Principal) -> MediaAssetModel:
        """Mark an asset for idempotent worker deletion."""
        asset = await self._get_owned(asset_id, principal, for_update=True)
        if asset.status in {AssetStatus.DELETING, AssetStatus.DELETED}:
            return asset
        asset.status = AssetStatus.DELETING
        asset.delete_requested_at = datetime.now(UTC)
        await self._session.commit()
        await self._refresh_queue_metrics()
        return asset

    async def _get_owned(
        self, asset_id: uuid.UUID, principal: Principal, *, for_update: bool
    ) -> MediaAssetModel:
        asset = await self._repository.get(asset_id, for_update=for_update)
        if asset is None:
            raise AssetNotFound()
        if not self._can_manage(asset, principal):
            raise AssetAccessDenied()
        return asset

    @staticmethod
    def _can_manage(asset: MediaAssetModel, principal: Principal) -> bool:
        return principal.role == "ADMIN" or asset.uploader_id == principal.user_id

    async def _delete_best_effort(self, object_key: str) -> None:
        try:
            await self._storage.delete_object(object_key)
        except MediaError:
            pass

    async def _refresh_queue_metrics(self) -> None:
        counts = await self._repository.queue_counts()
        PENDING_ASSETS.set(counts.pending)
        DELETION_QUEUE.set(counts.deleting)
