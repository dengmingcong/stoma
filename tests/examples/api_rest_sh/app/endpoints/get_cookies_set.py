"""Set cookies from query parameters。

Generated from OpenAPI: get-cookies-set
"""

from __future__ import annotations

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel, GetCookiesSetResponse
from ..router import router


@router.get("/cookies/set")
class GetCookiesSet(APIRoute):
    """Set cookies from query parameters。"""

    @property
    def on_200(self) -> JSONResponseSpec[GetCookiesSetResponse]:
        return JSONResponseSpec(status_code=200, media_type="application/json", model=GetCookiesSetResponse)

    @property
    def on_default(self) -> JSONResponseSpec[ErrorModel]:
        return JSONResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", model=ErrorModel
        )
