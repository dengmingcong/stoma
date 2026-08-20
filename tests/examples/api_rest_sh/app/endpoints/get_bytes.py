"""Return random bytes。

Generated from OpenAPI: get-bytes
"""

from __future__ import annotations

from stoma import APIRoute

from ..models import ErrorModel
from ..router import router


@router.get("/bytes/{n}")
class GetBytes(APIRoute[ErrorModel]):
    """Return random bytes。"""

    n: int
    """Number of bytes to return"""
    seed: int | None = None
    """Optional deterministic seed"""
