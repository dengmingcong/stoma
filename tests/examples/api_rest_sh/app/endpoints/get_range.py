"""Return bytes with Range support。

Generated from OpenAPI: get-range
"""

from __future__ import annotations

from stoma import APIRoute

from ..models import ErrorModel
from ..router import router


@router.get("/range/{n}")
class GetRange(APIRoute[ErrorModel]):
    """Return bytes with Range support。"""

    n: int
    """Number of bytes in the virtual resource"""
