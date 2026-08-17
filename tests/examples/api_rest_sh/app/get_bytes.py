"""Return random bytes。

Generated from OpenAPI: get-bytes
"""

from __future__ import annotations

from .models import GetBytesResponse
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/bytes/{n}")
class GetBytes(APIRoute[GetBytesResponse]):
    """Return random bytes。
    """
    n: int
    seed: int | None = None
