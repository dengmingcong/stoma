"""Require an API key query parameter。

Generated from OpenAPI: get-auth-api-key-query
"""

from __future__ import annotations

from typing import ClassVar

from stoma import APIRoute, JSONResponseSpec

from ..models import AuthResponseBody, ErrorModel
from ..router import router


@router.get("/auth/api-key-query")
class GetAuthApiKeyQuery(APIRoute):
    """Require an API key query parameter。"""

    on_200: ClassVar[JSONResponseSpec] = JSONResponseSpec(
        status_code=200, media_type="application/json", model=AuthResponseBody
    )
    on_default: ClassVar[JSONResponseSpec] = JSONResponseSpec(
        callable=lambda s: True, media_type="application/problem+json", model=ErrorModel
    )
    api_key: str | None = None
    """API key"""
