"""S3-compatible object-storage adapter."""

import asyncio
import time
from collections.abc import Callable
from typing import Any, TypeVar

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from media_service.application.contracts import ObjectStorage
from media_service.config import Settings
from media_service.domain.entities import PresignedPost, StoredObject
from media_service.domain.exceptions import StorageObjectNotFound, StorageUnavailable
from media_service.observability import S3_DURATION, S3_OPERATIONS

T = TypeVar("T")


class S3ObjectStorage(ObjectStorage):
    """Use separate internal and browser-visible S3 clients."""

    def __init__(self, settings: Settings) -> None:
        self._bucket = settings.s3_bucket
        common: dict[str, Any] = {
            "service_name": "s3",
            "aws_access_key_id": settings.s3_access_key,
            "aws_secret_access_key": settings.s3_secret_key,
            "region_name": settings.s3_region,
            "config": Config(
                signature_version="s3v4",
                s3={"addressing_style": settings.s3_addressing_style},
                connect_timeout=5,
                read_timeout=30,
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        }
        self._internal: Any = boto3.client(
            endpoint_url=settings.s3_internal_endpoint,
            **common,
        )
        self._public: Any = boto3.client(
            endpoint_url=settings.s3_public_endpoint,
            **common,
        )

    async def _call(self, operation: str, function: Callable[..., T], **kwargs: object) -> T:
        started = time.monotonic()
        try:
            result = await asyncio.to_thread(function, **kwargs)
            S3_OPERATIONS.labels(operation, "success").inc()
            return result
        except ClientError as exc:
            S3_OPERATIONS.labels(operation, "error").inc()
            code = str(exc.response.get("Error", {}).get("Code", ""))
            if code in {"404", "NoSuchKey", "NotFound"}:
                raise StorageObjectNotFound() from exc
            raise StorageUnavailable() from exc
        except (BotoCoreError, OSError) as exc:
            S3_OPERATIONS.labels(operation, "error").inc()
            raise StorageUnavailable() from exc
        finally:
            S3_DURATION.labels(operation).observe(time.monotonic() - started)

    async def create_presigned_post(
        self,
        *,
        key: str,
        content_type: str,
        size: int,
        asset_id: str,
        expires_in: int,
        inline: bool,
    ) -> PresignedPost:
        disposition = "inline" if inline else "attachment"
        fields = {
            "Content-Type": content_type,
            "Cache-Control": "public, max-age=31536000, immutable",
            "Content-Disposition": disposition,
            "x-amz-meta-asset-id": asset_id,
        }
        conditions: list[object] = [
            {"Content-Type": content_type},
            {"Cache-Control": fields["Cache-Control"]},
            {"Content-Disposition": disposition},
            {"x-amz-meta-asset-id": asset_id},
            ["content-length-range", size, size],
        ]
        result = await self._call(
            "presign_post",
            self._public.generate_presigned_post,
            Bucket=self._bucket,
            Key=key,
            Fields=fields,
            Conditions=conditions,
            ExpiresIn=expires_in,
        )
        return PresignedPost(
            url=str(result["url"]),
            fields={str(name): str(value) for name, value in result["fields"].items()},
        )

    async def head_object(self, key: str) -> StoredObject:
        result = await self._call(
            "head_object", self._internal.head_object, Bucket=self._bucket, Key=key
        )
        return StoredObject(
            size=int(result["ContentLength"]),
            content_type=str(result.get("ContentType", "")),
            metadata={str(k).lower(): str(v) for k, v in result.get("Metadata", {}).items()},
        )

    async def read_object(self, key: str, max_bytes: int) -> bytes:
        def read() -> bytes:
            try:
                response = self._internal.get_object(Bucket=self._bucket, Key=key)
                body = response["Body"]
                try:
                    data: bytes = body.read(max_bytes + 1)
                finally:
                    body.close()
                return data
            except ClientError as exc:
                code = str(exc.response.get("Error", {}).get("Code", ""))
                if code in {"404", "NoSuchKey", "NotFound"}:
                    raise StorageObjectNotFound() from exc
                raise StorageUnavailable() from exc
            except (BotoCoreError, OSError) as exc:
                raise StorageUnavailable() from exc

        started = time.monotonic()
        try:
            result = await asyncio.to_thread(read)
            S3_OPERATIONS.labels("get_object", "success").inc()
            return result
        except StorageObjectNotFound, StorageUnavailable:
            S3_OPERATIONS.labels("get_object", "error").inc()
            raise
        finally:
            S3_DURATION.labels("get_object").observe(time.monotonic() - started)

    async def delete_object(self, key: str) -> None:
        await self._call(
            "delete_object", self._internal.delete_object, Bucket=self._bucket, Key=key
        )

    async def check_bucket(self) -> None:
        await self._call("head_bucket", self._internal.head_bucket, Bucket=self._bucket)
