"""None。

Generated from OpenAPI: list-images
List available images
"""

from __future__ import annotations

from .models import ListImagesResponse, ErrorModel
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/images")
class ListImages(APIRoute[ListImagesResponse | ErrorModel]):
    """None。
    List available images
    """
    cursor: str | None = None
    format: str | None = None
    search: str | None = None
    limit: int | None = None
    per_page: int | None = None
