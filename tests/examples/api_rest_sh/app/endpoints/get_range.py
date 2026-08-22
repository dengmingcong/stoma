"""Return bytes with Range support。

Generated from OpenAPI: get-range
"""

from __future__ import annotations

from typing import ClassVar

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel
from ..router import router


@router.get("/range/{n}")
class GetRange(APIRoute):
    """Return bytes with Range support。"""

    on_default: ClassVar[JSONResponseSpec[ErrorModel]] = JSONResponseSpec(
        callable=lambda s: True, media_type="application/problem+json", model=ErrorModel
    )
    n: int
    """Number of bytes in the virtual resource"""
