"""Slowly stream bytes。

Generated from OpenAPI: get-drip
"""

from __future__ import annotations

from typing import ClassVar

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel
from ..router import router


@router.get("/drip")
class GetDrip(APIRoute):
    """Slowly stream bytes。"""

    on_default: ClassVar[JSONResponseSpec] = JSONResponseSpec(
        callable=lambda s: True, media_type="application/problem+json", model=ErrorModel
    )
    numbytes: int | None = None
    """Number of bytes to stream"""
    duration: str | None = None
    """Total duration over which bytes are emitted"""
    delay: str | None = None
    """Delay before streaming begins"""
    code: int | None = None
    """HTTP status code to return"""
