"""Return request cookies。

Generated from OpenAPI: get-cookies
"""

from __future__ import annotations

from stoma import APIRoute, ResponseSpec

from ..models import ErrorModel, GetCookiesResponse
from ..router import router


@router.get("/cookies")
class GetCookies(APIRoute):
    """Return request cookies。"""

    @property
    def on_200(self) -> ResponseSpec[GetCookiesResponse]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=GetCookiesResponse)

    @property
    def on_default(self) -> ResponseSpec[ErrorModel]:
        return ResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", expected_type=ErrorModel
        )
