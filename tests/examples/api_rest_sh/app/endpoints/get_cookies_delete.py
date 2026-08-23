"""Delete cookies named by query parameters。

Generated from OpenAPI: get-cookies-delete
"""

from __future__ import annotations

from stoma import APIRoute, ResponseSpec

from ..models import ErrorModel, GetCookiesDeleteResponse
from ..router import router


@router.get("/cookies/delete")
class GetCookiesDelete(APIRoute):
    """Delete cookies named by query parameters。"""

    @property
    def on_200(self) -> ResponseSpec[GetCookiesDeleteResponse]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=GetCookiesDeleteResponse)

    @property
    def on_default(self) -> ResponseSpec[ErrorModel]:
        return ResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", expected_type=ErrorModel
        )
