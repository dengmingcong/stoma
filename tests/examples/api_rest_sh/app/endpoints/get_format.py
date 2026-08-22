"""Return data using a specific media type。

Generated from OpenAPI: get-format
"""

from __future__ import annotations

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel
from ..router import router


@router.get("/formats/{format}")
class GetFormat(APIRoute):
    """Return data using a specific media type。"""

    format: str
    """Response format to encode"""

    @property
    def on_default(self) -> JSONResponseSpec[ErrorModel]:
        return JSONResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", model=ErrorModel
        )
