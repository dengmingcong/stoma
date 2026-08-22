"""Return random bytes。

Generated from OpenAPI: get-bytes
"""

from __future__ import annotations

from stoma import APIRoute, JSONResponseSpec

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
    def on_default(self) -> JSONResponseSpec[ErrorModel]:
        return JSONResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", model=ErrorModel
        )
