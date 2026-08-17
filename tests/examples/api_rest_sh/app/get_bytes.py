"""Return random bytes。

Generated from OpenAPI: get-bytes
"""

from __future__ import annotations

from .models import ErrorModel
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/bytes/{n}")
class GetBytes(APIRoute[ErrorModel]):
    """Return random bytes。
    """
    n: int
    seed: int | None = None
