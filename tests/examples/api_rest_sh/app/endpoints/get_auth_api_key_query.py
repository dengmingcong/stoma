"""Require an API key query parameter。

Generated from OpenAPI: get-auth-api-key-query
"""

from __future__ import annotations

from stoma import APIRoute, ResponseSpec

from ..models import AuthResponseBody, ErrorModel
from ..router import router


@router.get("/auth/api-key-query")
class GetAuthApiKeyQuery(APIRoute):
    """Require an API key query parameter。"""

    api_key: str | None = None
    """API key"""

    @property
    def on_200(self) -> ResponseSpec[AuthResponseBody]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=AuthResponseBody)

    @property
    def on_default(self) -> ResponseSpec[ErrorModel]:
        return ResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", expected_type=ErrorModel
        )
