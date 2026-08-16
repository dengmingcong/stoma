"""Exercise ETag conditional headers。

Generated from OpenAPI: get-etag
"""

from __future__ import annotations

from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/etag/{etag}")
class GetEtag(APIRoute):
    """Exercise ETag conditional headers。
    """
    etag: str
