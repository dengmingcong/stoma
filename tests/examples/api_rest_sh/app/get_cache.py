"""Return 304 when conditional request headers are present。

Generated from OpenAPI: get-cache
"""

from __future__ import annotations

from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/cache")
class GetCache(APIRoute):
    """Return 304 when conditional request headers are present。
    """
