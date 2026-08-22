"""Require HTTP Basic auth。

Generated from OpenAPI: get-auth-basic
"""

from __future__ import annotations

from stoma import APIRoute, JSONResponseSpec

from ..models import AuthResponseBody, ErrorModel
from ..router import router


@router.get("/auth/basic")
class GetAuthBasic(APIRoute):
    """Require HTTP Basic auth。"""

    @property
    def on_200(self) -> JSONResponseSpec[AuthResponseBody]:
        return JSONResponseSpec(status_code=200, media_type="application/json", model=AuthResponseBody)

    @property
    def on_default(self) -> JSONResponseSpec[ErrorModel]:
        return JSONResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", model=ErrorModel
        )
