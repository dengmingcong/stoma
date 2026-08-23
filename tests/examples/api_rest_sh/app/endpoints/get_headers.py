"""Return request headers。

Generated from OpenAPI: get-headers
"""

from __future__ import annotations

from stoma import APIRoute, ResponseSpec

from ..models import ErrorModel, GetHeadersResponse
from ..router import router


@router.get("/headers")
class GetHeaders(APIRoute):
    """Return request headers。"""

    @property
    def on_200(self) -> ResponseSpec[GetHeadersResponse]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=GetHeadersResponse)

    @property
    def on_default(self) -> ResponseSpec[ErrorModel]:
        return ResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", expected_type=ErrorModel
        )
