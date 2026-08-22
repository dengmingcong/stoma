"""Return random bytes。

Generated from OpenAPI: get-bytes
"""

from __future__ import annotations

from typing import ClassVar

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel
from ..router import router


@router.get("/bytes/{n}")
class GetBytes(APIRoute):
    """Return random bytes。"""

    on_default: ClassVar[JSONResponseSpec] = JSONResponseSpec(
        callable=lambda s: True, media_type="application/problem+json", model=ErrorModel
    )
    n: int
    """Number of bytes to return"""
    seed: int | None = None
    """Optional deterministic seed"""
