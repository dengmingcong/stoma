"""Set response headers from query parameters。

Generated from OpenAPI: get-response-headers
"""

from __future__ import annotations

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel, GetResponseHeadersResponse
from ..router import router


@router.get("/response-headers")
class GetResponseHeaders(APIRoute):
    """Set response headers from query parameters。"""

    @property
    def on_200(self) -> JSONResponseSpec[GetResponseHeadersResponse]:
        return JSONResponseSpec(status_code=200, media_type="application/json", model=GetResponseHeadersResponse)

    @property
    def on_default(self) -> JSONResponseSpec[ErrorModel]:
        return JSONResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", model=ErrorModel
        )
