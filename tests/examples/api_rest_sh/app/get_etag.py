"""Exercise ETag conditional headers。

Generated from OpenAPI: get-etag
"""

from __future__ import annotations

from stoma import APIRoute, APIRouter

from .models import ErrorModel

router = APIRouter()


@router.get("/etag/{etag}")
class GetEtag(APIRoute[ErrorModel]):
    """Exercise ETag conditional headers。"""

    etag: str
    """Opaque ETag value to return"""
