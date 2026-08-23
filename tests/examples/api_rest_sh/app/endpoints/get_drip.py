"""Slowly stream bytes。

Generated from OpenAPI: get-drip
"""

from __future__ import annotations

from stoma import APIRoute, EmptyResponseSpec, ResponseSpec

from ..models import ErrorModel
from ..router import router


@router.get("/drip")
class GetDrip(APIRoute):
    """Slowly stream bytes。"""

    numbytes: int | None = None
    """Number of bytes to stream"""
    duration: str | None = None
    """Total duration over which bytes are emitted"""
    delay: str | None = None
    """Delay before streaming begins"""
    code: int | None = None
    """HTTP status code to return"""

    @property
    def on_204(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=204,
        )

    @property
    def on_default(self) -> ResponseSpec[ErrorModel]:
        return ResponseSpec(
            status_code=lambda c: c not in [204],
            media_type="application/problem+json",
            expected_type=ErrorModel,
        )
