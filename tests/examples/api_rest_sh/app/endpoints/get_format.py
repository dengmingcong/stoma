"""Return data using a specific media type。

Generated from OpenAPI: get-format
"""

from __future__ import annotations

from typing import ClassVar

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel
from ..router import router


@router.get("/formats/{format}")
class GetFormat(APIRoute):
    """Return data using a specific media type。"""

    on_default: ClassVar[JSONResponseSpec] = JSONResponseSpec(
        callable=lambda s: True, media_type="application/problem+json", model=ErrorModel
    )
    format: str
    """Response format to encode"""
