"""Set cookies from query parameters。

Generated from OpenAPI: get-cookies-set
"""

from __future__ import annotations

from stoma import APIRoute, ResponseSpec

from ..models import ErrorModel, GetCookiesSetResponse
from ..router import router


@router.get("/cookies/set")
class GetCookiesSet(APIRoute):
    """Set cookies from query parameters。"""

    @property
    def on_200(self) -> ResponseSpec[GetCookiesSetResponse]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=GetCookiesSetResponse)

    @property
    def on_default(self) -> ResponseSpec[ErrorModel]:
        return ResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", expected_type=ErrorModel
        )
