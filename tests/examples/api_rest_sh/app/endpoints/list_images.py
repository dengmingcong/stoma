"""
Generated from OpenAPI: list-images
List available images
"""

from __future__ import annotations

from typing import ClassVar

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel, ListImagesResponse
from ..router import router


@router.get("/images")
class ListImages(APIRoute):
    """
    List available images
    """

    on_200: ClassVar[JSONResponseSpec] = JSONResponseSpec(
        status_code=200, media_type="application/json", model=ListImagesResponse
    )
    on_default: ClassVar[JSONResponseSpec] = JSONResponseSpec(
        callable=lambda s: True, media_type="application/problem+json", model=ErrorModel
    )
    cursor: str | None = None
    """Pagination cursor"""
    format: str | None = None
    """Filter by image format"""
    search: str | None = None
    """Case-insensitive search over image names"""
    limit: int | None = None
    """Maximum number of images to return"""
    per_page: int | None = None
    """Alias for limit"""
