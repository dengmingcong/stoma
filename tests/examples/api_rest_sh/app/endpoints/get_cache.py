"""Return 304 when conditional request headers are present。

Generated from OpenAPI: get-cache
"""

from __future__ import annotations

from stoma import APIRoute

from ..models import ErrorModel
from ..router import router


@router.get("/cache")
class GetCache(APIRoute[ErrorModel]):
    """Return 304 when conditional request headers are present。"""
