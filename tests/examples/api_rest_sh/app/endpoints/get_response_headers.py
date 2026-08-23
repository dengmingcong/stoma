"""Set response headers from query parameters。

Generated from OpenAPI: get-response-headers
"""

from __future__ import annotations

from stoma import APIRoute, ResponseSpec

from ..models import ErrorModel, GetResponseHeadersResponse
from ..router import router


@router.get("/response-headers")
class GetResponseHeaders(APIRoute):
    """Set response headers from query parameters。"""

    @property
    def on_200(self) -> ResponseSpec[GetResponseHeadersResponse]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=GetResponseHeadersResponse)

    @property
    def on_default(self) -> ResponseSpec[ErrorModel]:
        return ResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", expected_type=ErrorModel
        )
