"""Return a UUID。

Generated from OpenAPI: get-uuid
"""

from __future__ import annotations

from stoma import APIRouter, APIRoute
from .models import GetUuidResponse, ErrorModel

router = APIRouter()


@router.get("/uuid")
class GetUuid(APIRoute[GetUuidResponse | ErrorModel]):
    """Return a UUID。"""
