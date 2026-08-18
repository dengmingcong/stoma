"""Return a UUID。

Generated from OpenAPI: get-uuid
"""

from __future__ import annotations

from .models import GetUuidResponse, ErrorModel
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/uuid")
class GetUuid(APIRoute[GetUuidResponse | ErrorModel]):
    """Return a UUID。"""
