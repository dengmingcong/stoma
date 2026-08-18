"""Return a UUID。

Generated from OpenAPI: get-uuid
"""

from __future__ import annotations

from stoma import APIRoute, APIRouter

from .models import ErrorModel, GetUuidResponse

router = APIRouter()


@router.get("/uuid")
class GetUuid(APIRoute[GetUuidResponse | ErrorModel]):
    """Return a UUID。"""
