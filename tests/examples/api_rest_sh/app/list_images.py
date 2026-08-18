"""
Generated from OpenAPI: list-images
List available images
"""

from __future__ import annotations

from stoma import APIRoute, APIRouter

from .models import ErrorModel, ListImagesResponse

router = APIRouter()


@router.get("/images")
class ListImages(APIRoute[ListImagesResponse | ErrorModel]):
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
