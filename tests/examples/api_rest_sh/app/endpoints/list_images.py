"""
Generated from OpenAPI: list-images
List available images
"""

from __future__ import annotations

from stoma import APIRoute, ResponseSpec

from ..models import ErrorModel, ListImagesResponse
from ..router import router


@router.get("/images")
class ListImages(APIRoute):
    """
    List available images
    """

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

    @property
    def on_200(self) -> ResponseSpec[ListImagesResponse]:
        return ResponseSpec(
            status_code=200,
            media_type="application/json",
            expected_type=ListImagesResponse,
        )

    @property
    def on_default(self) -> ResponseSpec[ErrorModel]:
        return ResponseSpec(
            status_code=lambda c: c not in [200],
            media_type="application/problem+json",
            expected_type=ErrorModel,
        )
