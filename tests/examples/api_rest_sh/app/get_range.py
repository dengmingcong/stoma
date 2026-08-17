"""Return bytes with Range support。

Generated from OpenAPI: get-range
"""

from __future__ import annotations

from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/range/{n}")
class GetRange(APIRoute):
    """Return bytes with Range support。
    """
    n: int
