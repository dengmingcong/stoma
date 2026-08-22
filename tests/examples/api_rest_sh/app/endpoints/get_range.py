"""Return bytes with Range support。

Generated from OpenAPI: get-range
"""

from __future__ import annotations

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel
from ..router import router


@router.get("/range/{n}")
class GetRange(APIRoute):
    """Return bytes with Range support。"""

    n: int
    """Number of bytes in the virtual resource"""

    @property
    def on_default(self) -> JSONResponseSpec[ErrorModel]:
        return JSONResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", model=ErrorModel
        )
