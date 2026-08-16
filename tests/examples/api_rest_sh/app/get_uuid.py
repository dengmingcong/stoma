"""Return a UUID。

Generated from OpenAPI: get-uuid
"""

from __future__ import annotations

from .models import GetUuidResponse
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/uuid")
class GetUuid(APIRoute[GetUuidResponse]):
    """Return a UUID。
    """
