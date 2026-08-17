"""Return random bytes。

Generated from OpenAPI: get-bytes
"""

from __future__ import annotations

from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/bytes/{n}")
class GetBytes(APIRoute):
    """Return random bytes。
    """
    n: int
    seed: int | None = None
