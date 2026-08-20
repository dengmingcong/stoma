"""Return a UUID。

Generated from OpenAPI: get-uuid
"""

from __future__ import annotations

from stoma import APIRoute

from ..models import ErrorModel, GetUuidResponse
from ..router import router


@router.get("/uuid")
class GetUuid(APIRoute[GetUuidResponse | ErrorModel]):
    """Return a UUID。"""
