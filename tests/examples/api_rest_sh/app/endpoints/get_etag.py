"""Exercise ETag conditional headers。

Generated from OpenAPI: get-etag
"""

from __future__ import annotations

from stoma import APIRoute

from ..models import ErrorModel
from ..router import router


@router.get("/etag/{etag}")
class GetEtag(APIRoute[ErrorModel]):
    """Exercise ETag conditional headers。"""

    etag: str
    """Opaque ETag value to return"""
