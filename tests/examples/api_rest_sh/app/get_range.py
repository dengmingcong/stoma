"""Return bytes with Range support。

Generated from OpenAPI: get-range
"""

from __future__ import annotations

from stoma import APIRouter, APIRoute
from .models import ErrorModel

router = APIRouter()


@router.get("/range/{n}")
class GetRange(APIRoute[ErrorModel]):
    """Return bytes with Range support。"""

    n: int
    """Number of bytes in the virtual resource"""
