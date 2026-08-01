"""Unit tests for public-file safety policies."""

from io import BytesIO
from uuid import uuid4

import pytest
from PIL import Image

from media_service.domain.exceptions import (
    AssetAccessDenied,
    InvalidBinding,
    InvalidFilename,
    UnsupportedContentType,
)
from media_service.domain.policies import (
    authorize_upload,
    get_policy,
    sanitize_filename,
    validate_content,
)


def png_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (2, 3), "red").save(output, format="PNG")
    return output.getvalue()


def test_sanitize_filename_removes_paths_and_unsafe_characters() -> None:
    assert sanitize_filename("../Каталог/my hero.png") == "my-hero.png"
    with pytest.raises(InvalidFilename):
        sanitize_filename("..")


def test_admin_purpose_rejects_customer() -> None:
    with pytest.raises(AssetAccessDenied):
        authorize_upload(
            policy=get_policy("product_image"),
            user_id=uuid4(),
            role="CUSTOMER",
            entity_type="product",
            entity_id=uuid4(),
        )


def test_avatar_must_bind_to_current_user() -> None:
    with pytest.raises(AssetAccessDenied):
        authorize_upload(
            policy=get_policy("user_avatar"),
            user_id=uuid4(),
            role="CUSTOMER",
            entity_type="user",
            entity_id=uuid4(),
        )
    with pytest.raises(InvalidBinding):
        authorize_upload(
            policy=get_policy("user_avatar"),
            user_id=uuid4(),
            role="ADMIN",
            entity_type=None,
            entity_id=None,
        )


def test_validate_content_detects_real_image_and_dimensions() -> None:
    content = png_bytes()
    result = validate_content(content, "image/png", max_pixels=100)
    assert result.content_type == "image/png"
    assert result.width == 2
    assert result.height == 3
    assert len(result.sha256) == 64


def test_validate_content_rejects_declared_type_mismatch() -> None:
    with pytest.raises(UnsupportedContentType):
        validate_content(png_bytes(), "image/jpeg", max_pixels=100)
