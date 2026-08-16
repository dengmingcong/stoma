"""Return bytes with Range support。

Generated from OpenAPI: get-range
"""

from __future__ import annotations

from .models import GetRangeResponse
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/range/{n}")
class GetRange(APIRoute[GetRangeResponse]):
    """Return bytes with Range support。
    """
    n: int
