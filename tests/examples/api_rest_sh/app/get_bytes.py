"""Return random bytes。

Generated from OpenAPI: get-bytes
"""

from __future__ import annotations

from stoma import APIRoute, APIRouter

from .models import ErrorModel

router = APIRouter()


@router.get("/bytes/{n}")
class GetBytes(APIRoute[ErrorModel]):
    """Return random bytes。"""

    n: int
    seed: int | None = None
