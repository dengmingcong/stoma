"""list-images。

Generated from OpenAPI: list-images
List available images
"""

from __future__ import annotations

from .models import ListImagesResponse, ErrorModel
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/images")
class ListImages(APIRoute[ListImagesResponse | ErrorModel]):
    """list-images。
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
