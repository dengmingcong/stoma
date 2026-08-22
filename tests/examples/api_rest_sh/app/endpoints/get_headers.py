"""Return request headers。

Generated from OpenAPI: get-headers
"""

from __future__ import annotations

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel, GetHeadersResponse
from ..router import router


@router.get("/headers")
class GetHeaders(APIRoute):
    """Return request headers。"""

    @property
    def on_200(self) -> JSONResponseSpec[GetHeadersResponse]:
        return JSONResponseSpec(status_code=200, media_type="application/json", model=GetHeadersResponse)

    @property
    def on_default(self) -> JSONResponseSpec[ErrorModel]:
        return JSONResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", model=ErrorModel
        )
