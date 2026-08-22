"""Return request cookies。

Generated from OpenAPI: get-cookies
"""

from __future__ import annotations

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel, GetCookiesResponse
from ..router import router


@router.get("/cookies")
class GetCookies(APIRoute):
    """Return request cookies。"""

    @property
    def on_200(self) -> JSONResponseSpec[GetCookiesResponse]:
        return JSONResponseSpec(status_code=200, media_type="application/json", model=GetCookiesResponse)

    @property
    def on_default(self) -> JSONResponseSpec[ErrorModel]:
        return JSONResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", model=ErrorModel
        )
