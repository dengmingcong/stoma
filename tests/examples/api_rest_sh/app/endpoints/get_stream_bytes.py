"""Stream bytes in chunks。

Generated from OpenAPI: get-stream-bytes
"""

from __future__ import annotations

from typing import ClassVar

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel
from ..router import router


@router.get("/stream-bytes/{n}")
class GetStreamBytes(APIRoute):
    """Stream bytes in chunks。"""

    on_default: ClassVar[JSONResponseSpec[ErrorModel]] = JSONResponseSpec(
        callable=lambda s: True, media_type="application/problem+json", model=ErrorModel
    )
    n: int
    """Total number of bytes to stream"""
    chunk_size: int | None = None
    """Maximum bytes written per chunk"""
    seed: int | None = None
    """Optional deterministic seed"""
