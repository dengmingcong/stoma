"""Mock form login。

Generated from OpenAPI: post-login
Accepts an application/x-www-form-urlencoded username and password and returns a mock bearer token.
"""

from __future__ import annotations

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel, TokenResponseBody
from ..router import router


@router.post("/login")
class PostLogin(APIRoute):
    """Mock form login。

    Accepts an application/x-www-form-urlencoded username and password and returns a mock bearer token.
    """

    @property
    def on_200(self) -> JSONResponseSpec[TokenResponseBody]:
        return JSONResponseSpec(status_code=200, media_type="application/json", model=TokenResponseBody)

    @property
    def on_default(self) -> JSONResponseSpec[ErrorModel]:
        return JSONResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", model=ErrorModel
        )
