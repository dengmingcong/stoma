"""Delete cookies named by query parameters。

Generated from OpenAPI: get-cookies-delete
"""

from __future__ import annotations

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel, GetCookiesDeleteResponse
from ..router import router


@router.get("/cookies/delete")
class GetCookiesDelete(APIRoute):
    """Delete cookies named by query parameters。"""

    @property
    def on_200(self) -> JSONResponseSpec[GetCookiesDeleteResponse]:
        return JSONResponseSpec(status_code=200, media_type="application/json", model=GetCookiesDeleteResponse)

    @property
    def on_default(self) -> JSONResponseSpec[ErrorModel]:
        return JSONResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", model=ErrorModel
        )
