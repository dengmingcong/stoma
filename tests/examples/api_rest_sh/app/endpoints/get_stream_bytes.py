"""Stream bytes in chunks。

Generated from OpenAPI: get-stream-bytes
"""

from __future__ import annotations

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel
from ..router import router


@router.get("/stream-bytes/{n}")
class GetStreamBytes(APIRoute):
    """Stream bytes in chunks。"""

    n: int
    """Total number of bytes to stream"""
    chunk_size: int | None = None
    """Maximum bytes written per chunk"""
    seed: int | None = None
    """Optional deterministic seed"""

    @property
    def on_default(self) -> JSONResponseSpec[ErrorModel]:
        return JSONResponseSpec(
            status_code=lambda c: c not in [204], media_type="application/problem+json", model=ErrorModel
        )
