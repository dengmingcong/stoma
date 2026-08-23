"""Return random bytes。

Generated from OpenAPI: get-bytes
"""

from __future__ import annotations

from stoma import APIRoute, ResponseSpec

from ..models import ErrorModel
from ..router import router


@router.get("/bytes/{n}")
class GetBytes(APIRoute):
    """Return random bytes。"""

    n: int
    """Number of bytes to return"""
    seed: int | None = None
    """Optional deterministic seed"""

    @property
    def on_default(self) -> ResponseSpec[ErrorModel]:
        return ResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", expected_type=ErrorModel
        )
