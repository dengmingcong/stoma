"""Return an explicitly compressed response。

Generated from OpenAPI: get-gzip
"""

from __future__ import annotations

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel
from ..router import router


@router.get("/gzip")
class GetGzip(APIRoute):
    """Return an explicitly compressed response。"""

    @property
    def on_default(self) -> JSONResponseSpec[ErrorModel]:
        return JSONResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", model=ErrorModel
        )
