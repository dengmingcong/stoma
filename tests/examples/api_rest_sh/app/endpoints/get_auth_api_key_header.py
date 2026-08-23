"""Require an API key header。

Generated from OpenAPI: get-auth-api-key-header
"""

from __future__ import annotations

from stoma import APIRoute, ResponseSpec

from ..models import AuthResponseBody, ErrorModel
from ..router import router


@router.get("/auth/api-key-header")
class GetAuthApiKeyHeader(APIRoute):
    """Require an API key header。"""

    @property
    def on_200(self) -> ResponseSpec[AuthResponseBody]:
        return ResponseSpec(
            status_code=200,
            media_type="application/json",
            expected_type=AuthResponseBody,
        )

    @property
    def on_default(self) -> ResponseSpec[ErrorModel]:
        return ResponseSpec(
            status_code=lambda c: c not in [200],
            media_type="application/problem+json",
            expected_type=ErrorModel,
        )
