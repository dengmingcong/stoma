"""Return 304 when conditional request headers are present。

Generated from OpenAPI: get-cache
"""

from __future__ import annotations

from stoma import APIRoute, APIRouter

from .models import ErrorModel

router = APIRouter()


@router.get("/cache")
class GetCache(APIRoute[ErrorModel]):
    """Return 304 when conditional request headers are present。"""
