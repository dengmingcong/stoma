"""Return 304 when conditional request headers are present。

Generated from OpenAPI: get-cache
"""

from __future__ import annotations

from stoma import APIRoute, EmptyResponseSpec, ResponseSpec

from ..models import ErrorModel
from ..router import router


@router.get("/cache")
class GetCache(APIRoute):
    """Return 304 when conditional request headers are present。"""

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
